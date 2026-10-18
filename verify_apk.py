import zipfile
from pathlib import Path

apk = Path("MedicineReminder.apk")
with zipfile.ZipFile(apk) as z:
    assets = [n for n in z.namelist() if n.startswith("assets/")]
    print("Assets in APK:", assets)
    html = z.read("assets/index.html").decode("utf-8")
    print("Has <style> tag in index.html:", "<style>" in html)
    print("Has relative href='style.css':", 'href="style.css"' in html)
    print("Has relative src='app.js':", 'src="app.js"' in html)
    print("Size of index.html inside APK:", len(html), "bytes")
