import os
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= تنظیمات اصلی =================
DOMAINS = [
    "akamaihd.net",
    "a.akamaihd.net",
    "akamai-staging.net",
    "edgekey-staging.net",
    "edgesuite-staging.net",
    "akamaihd-staging.net",
    "akamaized-staging.net",
    "akamaiedge-staging.net",
    "akamaiorigin-staging.net",
    "a.akamaized-staging.net"
]

OUTPUT_FILE = "shir_khorshid_clean_ips.txt"

# ================= تابع تست مستقیم TLS و HTTP =================
def test_ip_for_all_domains(ip):
    """
    تست مستقیم اتصال TCP، انجام TLS Handshake با SNI اختصاصی هر دامنه
    و ارسال هدر HTTP برای اطمینان از پاسخ‌دهی سرورهای لبه آکامای.
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # دور زدن ارورهای عمومی سرتیفیکیت در اسکن عمومی
    
    # آی‌پی باید روی تک‌تک دامنه‌ها با موفقیت هدر برگرداند
    for domain in DOMAINS:
        try:
            # ۱. اتصال سوکت به پورت 443 آی‌پی آکامای
            with socket.create_connection((ip, 443), timeout=2.5) as sock:
                # ۲. شبیه‌سازی دست‌دادن TLS با لایه SNI دامنه مربوطه
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    # ۳. ارسال یک درخواست متنی ساده برای گرفتن تاییدیه لبه سرور
                    request = f"HEAD / HTTP/1.1\r\nHost: {domain}\r\nConnection: close\r\n\r\n"
                    ssock.sendall(request.encode('utf-8'))
                    
                    # خواندن پاسخ اولیه سرور
                    response = ssock.recv(128).decode('utf-8', errors='ignore')
                    
                    # اگر سرور آکامای پاسخ معتبر HTTP نداد، آی‌پی رد می‌شود
                    if not response.startswith("HTTP/"):
                        return None
        except Exception:
            # کوچکترین خطای شبکه، تایم‌اوت یا بلاک بودن پروتکل روی هر کدام از دامنه‌ها = رد شدن کل آی‌پی
            return None
            
    return ip

# ================= بدنه اصلی برنامه =================
def main():
    print("="*60)
    print("🚀 Shir-Khorshid Direct Akamai Scanner (High-Speed Multi-Thread)")
    print("="*60)
    
    # گسترش رنج مورد نظر شما به کل ساب‌نت /24 (تولید ۲۵۴ آی‌پی)
    ips_to_test = [f"23.215.0.{i}" for i in range(1, 255)]
    print(f"🎯 Generated {len(ips_to_test)} IPs from block: 23.215.0.0/24")
    print(f"🔎 Testing each IP against all {len(DOMAINS)} domains directly...\n")
    
    valid_ips = []
    
    # استفاده از ۳۰ رشته موازی برای بالا بردن فوق‌العاده سرعت تست مستقیم روی رانر
    with ThreadPoolExecutor(max_workers=30) as executor:
        # ثبت تسک‌ها در صف پردازش
        futures = {executor.submit(test_ip_for_all_domains, ip): ip for ip in ips_to_test}
        
        for future in as_completed(futures):
            ip = futures[future]
            try:
                result = future.result()
                if result:
                    print(f"🎉 JACKPOT! {ip} passed all 10 domains successfully.")
                    valid_ips.append(ip)
            except Exception as e:
                print(f"❌ Error during testing {ip}: {e}")
                
    # مدیریت فایل خروجی، ادغام با آی‌پی‌های قبلی و حذف موارد تکراری
    existing_ips = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            existing_ips = set(line.strip() for line in f if line.strip())
            
    all_clean_ips = existing_ips.union(set(valid_ips))
    
    with open(OUTPUT_FILE, "w") as f:
        for ip in sorted(all_clean_ips):
            f.write(f"{ip}\n")
            
    print("\n" + "="*60)
    print(f"💾 Scan Finished! Added {len(valid_ips)} new working IPs in this run.")
    print(f"📂 Total unique operational IPs in sub-link: {len(all_clean_ips)}")
    print("="*60)

if __name__ == "__main__":
    main()
