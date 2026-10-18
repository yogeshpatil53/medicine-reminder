from pathlib import Path

base_dir = Path(r"c:\Medicine Reminder")
static_dir = base_dir / "static"

# 1. Read style.css and index.html
style_css = (static_dir / "style.css").read_text(encoding="utf-8")
index_html = (static_dir / "index.html").read_text(encoding="utf-8")

# 2. Fix all leading slashes in index.html
index_html = index_html.replace('href="/manifest.json"', 'href="manifest.json"')
index_html = index_html.replace('href="/icon-192.png"', 'href="icon-192.png"')
index_html = index_html.replace('src="/app.js"', 'src="app.js"')
index_html = index_html.replace('href="/style.css"', 'href="style.css"')

import re

# 3. Inject full style.css directly into a <style> block inside <head>
# Remove any existing inlined style tag first to always stay in sync with style.css
index_html = re.sub(r'<style>[\s\S]*?</style>\s*', '', index_html)

style_tag = f"<style>\n/* INLINED STYLES FOR NATIVE ANDROID APK & PWA */\n{style_css}\n</style>"
index_html = index_html.replace(
    '<link rel="stylesheet" href="style.css">',
    f'<link rel="stylesheet" href="style.css">\n  {style_tag}'
)

(static_dir / "index.html").write_text(index_html, encoding="utf-8")
print("1. index.html updated with relative paths and inlined CSS!")

# 4. Update patch_android_files.py to add WebView file access flags
android_proj = Path(r"C:\Users\ALG GAMING\AndroidStudioProjects\medicinereminder")

main_activity_java = """package com.example.medicinereminder;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {

    private WebView webView;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                if (url.startsWith("tel:")) {
                    try {
                        Intent intent = new Intent(Intent.ACTION_DIAL, Uri.parse(url));
                        startActivity(intent);
                        return true;
                    } catch (Exception e) {
                        return false;
                    }
                }
                return false;
            }
        });

        webView.setWebChromeClient(new WebChromeClient());

        webView.loadUrl("file:///android_asset/index.html");

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (webView != null && webView.canGoBack()) {
                    webView.goBack();
                } else {
                    finish();
                }
            }
        });
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }
}
"""
(android_proj / "app" / "src" / "main" / "java" / "com" / "example" / "medicinereminder" / "MainActivity.java").write_text(main_activity_java, encoding="utf-8")
print("2. MainActivity.java updated with universal file access!")

# 5. Copy all static assets to Android project
assets_dest = android_proj / "app" / "src" / "main" / "assets"
assets_dest.mkdir(parents=True, exist_ok=True)

import shutil
for f in static_dir.iterdir():
    if f.is_file():
        shutil.copy2(f, assets_dest / f.name)

print("3. All assets synced to Android project assets folder!")
