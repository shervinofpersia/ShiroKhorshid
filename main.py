import os
import re
import time
import random
import requests

# ================= تنظیمات اصلی =================
# طبق پیشنهاد شما، فقط روی دو دامنه اصلی تست می‌شود تا سرعت و تعداد تست بالاتر برود
DOMAINS = [
    "akamaihd.net", 
    "a.akamaihd.net"
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
def get_random_ips_from_github(count_per_file=10):
    """برداشتن ۱۰ آی‌پی از هر فایل (مجموعا ۴۰ آی‌پی در هر دور)"""
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
                    all_selected_ips.extend(random_samples)
        except Exception as e:
            pass
            
    random.shuffle(all_selected_ips)
    return all_selected_ips

# ================= توابع تست Check-Host =================
def create_check_host_task(target_ip, domain):
    url = f"https://check-host.net/check-tcp?host={target_ip}:443&max_nodes=3&node=ir"
    headers = {'Accept': 'application/json'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("request_id")
        else:
            # اگر مسدود شویم، اینجا چاپ می‌کند تا دلیل سرعت بالا را بفهمیم
            print(f"   ⚠️ API Blocked us! Status: {response.status_code}. Sleeping 15s...")
            time.sleep(15) 
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")
    return None

def get_check_host_result(request_id):
    url = f"https://check-host.net/check-result/{request_id}"
    headers = {'Accept': 'application/json'}
    time.sleep(6) # حتما باید ۶ ثانیه صبر کنیم تا نودها جواب بدهند
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            results = response.json()
            for node, data in results.items():
                if "ir" in node and data is not None:
                    if any(item.get('status') == 1 for item in data if isinstance(item, dict)):
                        return True
    except Exception:
        pass
    return False

# ================= توابع مدیریت فایل خروجی =================
def save_clean_ips(new_ips):
    existing_ips = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            existing_ips = set(line.strip() for line in f if line.strip())
    
    all_clean_ips = existing_ips.union(set(new_ips))
    
    with open(OUTPUT_FILE, "w") as f:
        for ip in sorted(all_clean_ips):
            f.write(f"{ip}\n")
    print(f"\n💾 Saved {len(new_ips)} new IPs. Total unique IPs: {len(all_clean_ips)}")

# ================= بدنه اصلی اسکریپت =================
def main():
    print("="*50)
    print("🚀 Starting Shir-Khorshid Akamai Scanner (Optimized)")
    print("="*50)
    
    # گرفتن ۴۰ آی‌پی رندوم در هر اجرا
    ips_to_test = get_random_ips_from_github(count_per_file=10)
    print(f"\n🎯 Loaded {len(ips_to_test)} random IPs. Testing on 2 main domains...")
    
    valid_ips = []

    for index, ip in enumerate(ips_to_test, 1):
        print(f"\n[{index}/{len(ips_to_test)}] Testing IP: {ip}")
        ip_passed_all = True
        
        for domain in DOMAINS:
            req_id = create_check_host_task(ip, domain)
            
            if req_id:
                is_working = get_check_host_result(req_id)
                if not is_working:
                    print(f"   ❌ Blocked on {domain}.")
                    ip_passed_all = False
                    break 
                else:
                    print(f"   ✅ Clean on {domain}")
            else:
                ip_passed_all = False
                break
            
            time.sleep(4) # وقفه حیاتی برای جلوگیری از بلاک شدن توسط چک‌هاست
                
        if ip_passed_all:
            print(f"   🎉 SUCCESS! IP is fully clean.")
            valid_ips.append(ip)

    if valid_ips:
        save_clean_ips(valid_ips)
    else:
        print("\n⚠️ No valid IPs found in this round.")

if __name__ == "__main__":
    main()
