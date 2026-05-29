import os
import re
import time
import random
import requests

# ================= تنظیمات اصلی =================
DOMAINS = [
    "akamaihd.net", "a.akamaihd.net", "akamai-staging.net", 
    "edgekey-staging.net", "edgesuite-staging.net", "akamaihd-staging.net", 
    "akamaized-staging.net", "akamaiedge-staging.net", "akamaiorigin-staging.net", 
    "a.akamaized-staging.net"
]

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/shervinofpersia/Akamai/5a602ab2751fbca4d789fe6d24f9468b2c897427/ip_lists/"
AKAMAI_FILE_NAMES = [
    "akamai_as20940.txt",
    "akamai_cached.txt",
    "akamai_cidr.txt",
    "akamai_ipv4.txt"
]

OUTPUT_FILE = "shir_khorshid_clean_ips.txt"

# ================= توابع دریافت آی‌پی =================
def get_random_ips_from_github(count_per_file=3):
    """خواندن لیست آی‌پی‌ها از گیت‌هاب شیر و خورشید و انتخاب رندوم"""
    all_selected_ips = []
    print("📡 Connecting to GitHub to fetch Akamai IP lists...")
    
    for file_name in AKAMAI_FILE_NAMES:
        url = GITHUB_RAW_BASE + file_name
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                ips_in_file = re.findall(r'[0-9]+(?:\.[0-9]+){3}', response.text)
                if ips_in_file:
                    sample_size = min(count_per_file, len(ips_in_file))
                    random_samples = random.sample(ips_in_file, sample_size)
                    print(f"   🔹 Fetched {len(ips_in_file)} IPs from '{file_name}' -> Selected {sample_size}.")
                    all_selected_ips.extend(random_samples)
            else:
                print(f"   ⚠️ Failed to fetch {file_name} (Status: {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error fetching {file_name}: {e}")
            
    random.shuffle(all_selected_ips)
    return all_selected_ips

# ================= توابع تست Check-Host =================
def create_check_host_task(target_ip, domain, node_country="ir"):
    """ایجاد تسک تست TCP روی پورت 443"""
    url = f"https://check-host.net/check-tcp?host={target_ip}:443&max_nodes=3&node={node_country}"
    headers = {'Accept': 'application/json'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("request_id")
        elif response.status_code == 429:
            print("   ⚠️ Check-Host API Rate Limit hit. Waiting 10 seconds...")
            time.sleep(10)
    except Exception as e:
        print(f"   ❌ Error creating task: {e}")
    return None

def get_check_host_result(request_id):
    """گرفتن نتیجه تسک از نودهای ایران"""
    url = f"https://check-host.net/check-result/{request_id}"
    headers = {'Accept': 'application/json'}
    time.sleep(6) # صبر برای پاسخ نودها
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            results = response.json()
            for node, data in results.items():
                if "ir" in node and data is not None:
                    # بررسی موفقیت اتصال (status == 1)
                    if any(item.get('status') == 1 for item in data if isinstance(item, dict)):
                        return True
    except Exception as e:
        print(f"   ❌ Error fetching result: {e}")
    return False

# ================= توابع مدیریت فایل خروجی =================
def save_clean_ips(new_ips):
    """ذخیره آی‌پی‌ها و حذف موارد تکراری برای تمیز ماندن ساب‌لینک"""
    existing_ips = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            existing_ips = set(line.strip() for line in f if line.strip())
    
    # ترکیب آی‌پی‌های قدیمی با جدید و حذف تکراری‌ها
    all_clean_ips = existing_ips.union(set(new_ips))
    
    with open(OUTPUT_FILE, "w") as f:
        for ip in sorted(all_clean_ips):
            f.write(f"{ip}\n")
    print(f"\n💾 Saved {len(new_ips)} new IPs. Total unique IPs in file: {len(all_clean_ips)}")

# ================= بدنه اصلی اسکریپت =================
def main():
    print("="*50)
    print("🚀 Starting Shir-Khorshid Akamai Scanner...")
    print("="*50)
    
    ips_to_test = get_random_ips_from_github(count_per_file=3)
    print(f"\n🎯 Total unique IPs to scan in this run: {len(ips_to_test)}")
    
    valid_ips = []

    for index, ip in enumerate(ips_to_test, 1):
        print(f"\n[{index}/{len(ips_to_test)}] Crucial Test for IP: {ip}")
        ip_passed_all = True
        
        for domain in DOMAINS:
            print(f"   -> Testing on {domain}...")
            req_id = create_check_host_task(ip, domain)
            
            if req_id:
                is_working = get_check_host_result(req_id)
                if not is_working:
                    print(f"   ❌ Blocked/Failed on {domain}. Skipping IP.")
                    ip_passed_all = False
                    break # به محض شکست در یک دامنه، آی‌پی رد می‌شود
                else:
                    print(f"   ✅ Clean response on {domain}")
            else:
                ip_passed_all = False
                break
            
            time.sleep(2) # وقفه برای جلوگیری از بلاک شدن توسط API
                
        if ip_passed_all:
            print(f"   🎉 JACKPOT! {ip} passed all tests inside Iran network.")
            valid_ips.append(ip)

    if valid_ips:
        save_clean_ips(valid_ips)
    else:
        print("\n⚠️ No valid IPs found in this run. Better luck next time!")

if __name__ == "__main__":
    main()
