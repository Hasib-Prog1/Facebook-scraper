import requests
from parsel import Selector
import json
import time
import re
from urllib.parse import unquote


def get_data(url):
    session = requests.Session()
    
    
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'dpr': '1',
        'priority': 'u=0, i',
        'sec-ch-prefers-color-scheme': 'light',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="141.0.7390.122", "Not?A_Brand";v="8.0.0.0", "Chromium";v="141.0.7390.122"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"10.0.0"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'viewport-width': '1366',
    }
    
    

    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1} for {url}")
            
            # First try with normal www
            print(f"Trying with www.facebook.com...")
            resp = session.get(
                url, 
                headers=headers,
            
                timeout=30,
                allow_redirects=True
            )
            
            # Handle redirects explicitly
            if resp.history:
                print(f"Request was redirected {len(resp.history)} times")
                for r in resp.history:
                    print(f"Redirect: {r.status_code} - {r.url}")
                print(f"Final URL: {resp.url}")
            
          
            content_check = resp.text.lower()
            if resp.status_code != 200 or "login" in resp.url.lower() or "login" in content_check[:1000] or len(content_check) < 1000:
                print("Initial request unsuccessful, trying alternatives...")
                
               
                print("Trying mobile version...")
                mobile_url = url.replace("www.facebook.com", "m.facebook.com")
                mobile_headers = headers.copy()
                mobile_headers['user-agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
                resp = session.get(
                    mobile_url,
                    headers=mobile_headers,
                   
                    timeout=30,
                    allow_redirects=True
                )
                
                # If mobile didn't work, try web version
                if resp.status_code != 200 or "login" in resp.url.lower() or "login" in resp.text.lower()[:1000]:
                    print("Trying web.facebook.com...")
                    web_url = url.replace("www.facebook.com", "web.facebook.com")
                    resp = session.get(
                        web_url,
                        headers=headers,
                        
                        timeout=30,
                        allow_redirects=True
                    )
                    
            # Final status check
            if resp.status_code == 200:
                content_length = len(resp.text)
                print(f"Response received. Content length: {content_length} bytes")
                
                selector = Selector(text=resp.text)
                
                # Try multiple selectors for script tags
                script = []
                
                # Try the standard script selector
                standard_scripts = selector.css('script[type="application/json"][data-sjs]::text').getall()
                if standard_scripts:
                    script.extend(standard_scripts)
                    print(f"Found {len(standard_scripts)} standard script tags")
                
                # Try alternative selectors
                alt_scripts = selector.css('script[type="application/json"]::text').getall()
                if alt_scripts:
                    script.extend([s for s in alt_scripts if s not in script])
                    print(f"Found {len(alt_scripts)} alternative script tags")
                
                # Try getting any scripts with JSON content
                other_scripts = selector.css('script:contains("{")::text').getall()
                if other_scripts:
                    for s in other_scripts:
                        if s not in script and "{" in s and "}" in s:
                            script.append(s)
                    print(f"Found {len(other_scripts)} other potential JSON scripts")
                
                if script:
                    print(f"Total unique script tags found: {len(script)}")
                    return script, resp.text
                
                print("No script tags found, retrying...")
                
                # Save the HTML for debugging if no scripts found
                with open('debug_output.html', 'w', encoding='utf-8') as f:
                    f.write(resp.text)
            else:
                print(f"Status code: {resp.status_code}")
                print(f"Response headers: {resp.headers}")
            
            # Exponential backoff
            sleep_time = (2 ** attempt) + 1
            print(f"Waiting {sleep_time} seconds before retry...")
            time.sleep(sleep_time)
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + 1
                print(f"Waiting {sleep_time} seconds before retry...")
                time.sleep(sleep_time)
            continue
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + 1
                print(f"Waiting {sleep_time} seconds before retry...")
                time.sleep(sleep_time)
            continue
    
    raise Exception("Failed to get data after 3 tries")


def parse_scripts(script_data):
    parsed_data = []
    for i, item in enumerate(script_data):
        try:
            data = json.loads(item)
            parsed_data.append(data)
            print(f"Successfully parsed script {i + 1}")
        except json.JSONDecodeError as e:
            print(f"Failed to parse script {i + 1}: {str(e)}")
            continue
    print(f"Successfully parsed {len(parsed_data)} out of {len(script_data)} scripts")
    return parsed_data


def extract_actual_url(url):
    """Extract the actual URL from Facebook's redirect link"""
    if not url:
        return None
    if "l.facebook.com/l.php?u=" in url:
        try:
            # Extract the URL from Facebook's redirect
            actual_url = url.split("l.facebook.com/l.php?u=")[1].split("&")[0]
            # URL decode the string
            return unquote(actual_url)
        except:
            return url
    return url


def safe_get_nested(data, *keys):
    """Safely get nested dictionary values"""
    try:
        for key in keys:
            if isinstance(data, (dict, list)) and key < len(data) if isinstance(data, list) else key in data:
                data = data[key]
            else:
                return None
        return data
    except (KeyError, IndexError, TypeError):
        return None


def _find_value(obj, key):
    """
    Recursively search through nested dict/list structures to find a specific key.
    Returns the first non-empty value found, otherwise None.
    """
    if isinstance(obj, dict):
        # direct match
        if key in obj and obj[key]:
            return obj[key]

        # search deeper in dict values
        for v in obj.values():
            res = _find_value(v, key)
            if res:
                return res

    elif isinstance(obj, list):
        for item in obj:
            res = _find_value(item, key)
            if res:
                return res

    return None


def get_value(data, key):
    """
    Recursively search for a given key inside the nested structure.
    """
    if not isinstance(data, dict):
        return None

    try:
        base = data.get("filtered_0")
        if base and len(base) > 0:
            r0 = base[0].get("require") if isinstance(base[0], dict) else None
            if r0 and len(r0) > 0:
                try:
                    candidate_require = r0[0][3][0].get("__bbox", {}).get("require")
                except (IndexError, AttributeError):
                    candidate_require = None

                if isinstance(candidate_require, list):
                    for entry in candidate_require:
                        res = _find_value(entry, key)
                        if res:
                            return res

        # fallback
        if base:
            for top_item in base:
                res = _find_value(top_item, key)
                if res:
                    return res
    except Exception as e:
        print(f"Error while getting value for key {key}: {str(e)}")
        return None

    return None


def filter_data(data, key):
    def contains_key(obj):
        if isinstance(obj, dict):
            if key in obj:
                return True
            return any(contains_key(v) for v in obj.values())
        elif isinstance(obj, list):
            return any(contains_key(i) for i in obj)
        return False
    return [item for item in data if contains_key(item)]


def process_data(parsed_data):
    return {
        "filtered_0": filter_data(parsed_data, "category_name"),
        "filtered_1": filter_data(parsed_data, "profile_type_name_for_content"),
        "filtered_2": filter_data(parsed_data, "profile_name"),
        "filtered_3": filter_data(parsed_data, "username_for_profile"),
    }


def hasib(data, original_url):
    if not data:
        return {
            "facebookUrl": original_url,  # Return original URL even if no data
            "category_name": None,
            "title": None,
            "intro": None,
            "pageId": None,
            "Id": None,
            "pageName": None
        }

    try:
        # Always use the original input URL instead of extracting from data
        facebookUrl = original_url
    except:
        facebookUrl = None

    try:
        category_name = get_value(data, "category_name")
    except:
        category_name = None

    try:
        title = get_value(data, "profile_name")
    except:
        title = None

    try:
        intro = get_value(data, "best_description")
    except:
        intro = None

    try:
        pageId = get_value(data, "id")
    except:
        pageId = None

    try:
        filtered_3 = safe_get_nested(data, "filtered_3")
        if filtered_3 and isinstance(filtered_3, list) and filtered_3:
            Id = safe_get_nested(
                filtered_3[0], "require", 0, 3, 0, "__bbox", "require", 9, 3, 1,
                "__bbox", "result", "data", "user", "profile_header_renderer",
                "user", "profile_tabs", "profile_user", "delegate_page", "id"
            )
        else:
            Id = None
    except:
        Id = None

    try:
        pageName = facebookUrl.split("facebook.com/")[1].split("/")[0] if facebookUrl else None
    except:
        pageName = None

    return {
        "facebookUrl": facebookUrl,
        "category_name": category_name,
        "title": title,
        "intro": intro,
        "pageId": pageId,
        "Id": Id,
        "pageName": pageName
    }


def hasib1(data):
    if not data:
        return {"services": None}

    try:
        services = safe_get_nested(
            data, "filtered_1", 0, "require", 0, 3, 0, "__bbox", "require", 21, 3, 1,
            "__bbox", "result", "data", "profile_tile_sections", "edges", 0,
            "node", "profile_tile_views", "nodes", 1, "view_style_renderer",
            "view", "profile_tile_items", "nodes", 7, "node", "timeline_context_item",
            "renderer", "context_item", "title", "text"
        )
    except:
        services = None

    return {
        "services": services,
    }


def hasib2(data):
    if not data:
        return {"followers": None, "following": None}

    try:
        profile_header = safe_get_nested(
            data, "filtered_3", 0, "require", 0, 3, 0, "__bbox", "require", 9, 3, 1,
            "__bbox", "result", "data", "user", "profile_header_renderer", "user",
            "profile_social_context", "content"
        )
        
        followers = safe_get_nested(profile_header, 0, "text", "text") if profile_header else None
        following = safe_get_nested(profile_header, 1, "text", "text") if profile_header else None
    except:
        followers = None
        following = None

    return {
        "followers": followers,
        "following": following
    }


def hasib4(html_content):
    sel = Selector(text=html_content)
    content = sel.css('meta[name="description"]::attr(content)').get()

    likes = None
    were_here = None

    if content:
        likes_match = re.search(r'([\d,]+)\s*likes', content)
        likes = likes_match.group(1).replace(',', '') if likes_match else None

        were_here_match = re.search(r'([\d,]+)\s*were here', content)
        were_here = were_here_match.group(1).replace(',', '') if were_here_match else None

    return {"likes": likes, "were_here": were_here}


def extract_social_media_from_filtered_data(data):
    social_accounts = {
        "tiktok": [],
        "instagram": [],
        "Social_link": [],
        "emails": [],
        "twitter": []
    }
    
    def process_timeline_context_item(item):
        if not isinstance(item, dict):
            return
            
        # First check if this item itself is an ExternalUrl
        if item.get("__typename") == "ExternalUrl" or item.get("type") == "ExternalUrl":
            url = item.get("external_url", "") or item.get("url", "")
            text = item.get("text", "") or item.get("display_text", "")
            title = item.get("title", {})
            if isinstance(title, dict):
                text = title.get("text", text) or title.get("display_text", text)
            
            if url:
                actual_url = extract_actual_url(url)
                if actual_url:
                    if "twitter.com" in actual_url.lower():
                        username = actual_url.split("twitter.com/")[-1].split("?")[0].strip("/")
                        if username and "/" not in username:
                            social_accounts["twitter"].append({
                                "username": username,
                                "url": actual_url,
                                "text": text
                            })
                    else:
                        social_accounts["Social_link"].append({
                            "text": text,
                            "url": actual_url
                        })

        # Then check the renderer structure
        renderer = item.get("renderer", {})
        if isinstance(renderer, dict):
            typename = renderer.get("__typename")
            if typename == "ContextItemDefaultRenderer":
                context_item = renderer.get("context_item", {})
                title = context_item.get("title", {})
                if isinstance(title, dict):
                    text = title.get("text", "")
                    ranges = title.get("ranges", [])
                    
                    # Look for URLs in ranges
                    for range_item in ranges:
                        entity = range_item.get("entity", {})
                        if entity.get("__typename") == "ExternalUrl":
                            url = entity.get("external_url", "")
                            if url:
                                actual_url = extract_actual_url(url)
                                if actual_url:
                                    if "twitter.com" in actual_url.lower() or "x.com" in actual_url.lower():
                                        username = actual_url.split("twitter.com/")[-1].split("?")[0].strip("/") if "twitter.com" in actual_url.lower() else actual_url.split("x.com/")[-1].split("?")[0].strip("/")
                                        if username and "/" not in username and username != "share":
                                            social_accounts["twitter"].append({
                                                "username": username,
                                                "url": actual_url,
                                                "text": text or username
                                            })
                                    elif "instagram.com" in actual_url.lower():
                                        username = actual_url.split("instagram.com/")[-1].split("?")[0].strip("/")
                                        social_accounts["instagram"].append({
                                            "platform": "instagram",
                                            "username": username,
                                            "display_name": text,
                                            "url": actual_url
                                        })
                                    elif "tiktok.com" in actual_url.lower():
                                        username = actual_url.split("@")[-1].split("?")[0] if "@" in actual_url else actual_url.split("/")[-1].split("?")[0]
                                        social_accounts["tiktok"].append({
                                            "platform": "tiktok",
                                            "username": username,
                                            "display_name": text,
                                            "url": actual_url
                                        })
                                    else:
                                        social_accounts["Social_link"].append({
                                            "text": text,
                                            "url": actual_url
                                        })
                    
                    if text and "@" in text and "." in text:  # Basic email validation
                        social_accounts["emails"].append({"email": text})
                    elif text and ("." in text and "/" in text or "www." in text.lower()):  # Basic website validation
                        social_accounts["Social_link"].append({
                            "text": text,
                            "url": text
                        })

    if isinstance(data, dict):
        # Check for timeline_context_item
        if "timeline_context_item" in data:
            context_item = data.get("timeline_context_item", {})
            process_timeline_context_item(context_item)
            
            # Also check the nodes array if it exists
            if isinstance(context_item, dict):
                nodes = context_item.get("nodes", [])
                if isinstance(nodes, list):
                    for node in nodes:
                        if isinstance(node, dict):
                            timeline_item = node.get("timeline_context_item")
                            if timeline_item:
                                process_timeline_context_item(timeline_item)

        # Recursively search through all values
        for value in data.values():
            if isinstance(value, (dict, list)):
                recursive_results = extract_social_media_from_filtered_data(value)
                for platform in social_accounts:
                    social_accounts[platform].extend(recursive_results[platform])
    
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                recursive_results = extract_social_media_from_filtered_data(item)
                for platform in social_accounts:
                    social_accounts[platform].extend(recursive_results[platform])
    
    return social_accounts


def extract_websites_from_filtered_data(filtered_data):
    """Extract website URLs from filtered data and save to output.json"""
    websites = []
    
    def find_websites_in_data(item):
        if isinstance(item, dict):
            # Check if this is a timeline_context_item with renderer
            if 'timeline_context_item' in item:
                renderer = item['timeline_context_item'].get('renderer', {})
                if renderer.get('__typename') == 'WebsiteContextItemRenderer':
                    context_item = renderer.get('context_item', {})
                    # Try plaintext_title first, then title
                    website_text = (
                        context_item.get('plaintext_title', {}).get('text') or 
                        context_item.get('title', {}).get('text')
                    )
                    if website_text:
                        websites.append(website_text)
            
            # Recursively process all dictionary values
            for value in item.values():
                if isinstance(value, (dict, list)):
                    find_websites_in_data(value)
        elif isinstance(item, list):
            # Recursively process all list items
            for sub_item in item:
                find_websites_in_data(sub_item)
    
    # Start the recursive search from the filtered_data
    find_websites_in_data(filtered_data)
    
    # Remove duplicates while preserving order
    unique_websites = list(dict.fromkeys(websites))
    
    # Save results
    result = {"websites": unique_websites}
    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # Print results
    if unique_websites:
        print("\nFound websites:")
        for website in unique_websites:
            print(f"- {website}")
        return unique_websites
    else:
        print("\nNo websites found")
        return []

def main():
    urls = [
        "https://www.facebook.com/mrbeast",
        "https://www.facebook.com/Cristiano",
        "https://www.facebook.com/iamShakibKhanbd",
        "https://www.facebook.com/leomessi",
        "https://www.facebook.com/IamSRK",
        "https://www.facebook.com/BeingSalmanKhan",
        "https://www.facebook.com/bff.football",
        "https://www.facebook.com/bcbtigercricket",
        "https://www.facebook.com/nusraatfariaofficial/",
        "https://www.facebook.com/adhorakhanofficial/",
        "https://www.facebook.com/bdmaruf.Official/",
        "https://www.facebook.com/MakhnunActress/",
        "https://www.facebook.com/teamsiamahmed/",
        "https://www.facebook.com/WillSmith/",
        "https://web.facebook.com/emmawatson/",
        "https://web.facebook.com/neymarjr",
        "https://www.facebook.com/Zendaya/",
        "https://www.facebook.com/tawsifur.rahman.75/",
        "https://www.facebook.com/fatema.tanvir.792/",
        "https://www.facebook.com/official.sakibul.bashar/",
    ]

    print("⏳ Starting data collection...")
    all_data = []
    all_websites = []

    for url in urls:
        try:
            print(f"\nProcessing {url}...")
            script_data, html_content = get_data(url)
            
            if not script_data:
                print(f"No script data found for {url}")
                continue

            parsed_data = parse_scripts(script_data)
            if not parsed_data:
                print(f"Could not parse script data for {url}")
                continue

            filtered_data = process_data(parsed_data)
            if not filtered_data:
                print(f"Could not filter data for {url}")
                continue

            # Extract websites from filtered data
            found_websites = extract_websites_from_filtered_data(filtered_data)
            
            # Initialize merged_data
            merged_data = {}

            # Merge data from all functions, passing the original URL
            merged_data.update(hasib(filtered_data, url))  # Pass original URL
            merged_data.update(hasib1(filtered_data))
            merged_data.update(hasib2(filtered_data))
            merged_data.update(hasib4(html_content))
            
            # Add website field
            if found_websites:
                # Take the first website as the main website
                merged_data["website"] = found_websites[0]

            # Extract social media accounts from filtered data
            all_social_accounts = {"Social_link": [], "tiktok": [], "instagram": [], "emails": [], "twitter": []}
            
            for key, value in filtered_data.items():
                if value:  # Make sure the value is not None
                    social_accounts = extract_social_media_from_filtered_data(value)
                    for platform in all_social_accounts:
                        all_social_accounts[platform].extend(social_accounts[platform])

            # Add social media data to merged_data
            merged_data.update({
                "tiktok_accounts": all_social_accounts["tiktok"],
                "instagram_accounts": all_social_accounts["instagram"],
                "twitter_accounts": all_social_accounts["twitter"],
                "Social_link": all_social_accounts["Social_link"],
                "emails": all_social_accounts["emails"]
            })

            all_data.append(merged_data)
            print(f"✅ Successfully processed {url}")

        except Exception as e:
            print(f"❌ Error processing {url}: {str(e)}")
            continue

    # Save data to output.json
    if all_data:
        # Save to output.json
        with open('output.json', 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        # Print summary of websites found
        websites_found = [data.get('website') for data in all_data if data.get('website')]
        if websites_found:
            print("\nWebsites found in profiles:")
            for website in websites_found:
                print(f"- {website}")
        
        print(f"\n Data collection complete! Found data for {len(all_data)} profiles.")
    else:
        print("\n No data was collected successfully.")

if __name__ == "__main__":
    main()