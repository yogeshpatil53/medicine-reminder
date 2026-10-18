# 💊 MedRemind - Smart Medicine Reminder & Health Assistant

[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20Web%20PWA-2563EB.svg)](https://github.com/yogeshpatil53/medicine-reminder)
[![Status](https://img.shields.io/badge/Status-Active%20%26%20Ready-10B981.svg)](https://github.com/yogeshpatil53/medicine-reminder)

MedRemind is a modern, responsive, and reliable medicine reminder application designed to help patients and caregivers manage medication schedules, sound alarms with custom or clinical ringtones, and quickly reach emergency contacts.

---

## 📱 Download the Android App (APK)

Anyone with an Android phone can download and install the app directly:

👉 **[Direct APK Download Link (8.9 MB)](https://github.com/yogeshpatil53/medicine-reminder/raw/main/MedicineReminder.apk)**

### How to Install on Android:
1. Download **`MedicineReminder.apk`** to your phone.
2. Tap the downloaded file in your browser or **Files** / **Downloads** app.
3. If prompted with *"Install unknown apps"*, tap **Settings** and toggle **"Allow from this source"**.
4. Tap **Install** and open **MedRemind**! 🎉

---

## ✨ Key Features

- 🔐 **Dedicated Login & Registration First:** Secure authentication flow on first launch.
- ⚡ **Direct Entry on Subsequent Visits:** Automatic session persistence remembers your account and directly enters the app without asking for login again.
- ⏰ **Smart Medication Schedules:** Track morning, afternoon, and evening doses with 12-hour AM/PM formats and dosage instructions.
- 🎵 **Customizable Alarm Ringtones:**
  - 🔔 Gentle Medical Chime *(Ascending 4-tone pleasant reminder)*
  - 🩺 Digital Hospital Beep *(Clinical dual-pulse alert)*
  - 🚨 Urgent Wake-Up Siren *(High-attention alert)*
  - 🧘 Peaceful Zen Bell *(Harmonic singing bowl)*
  - 🎵 Cheerful Marimba *(Upbeat melody)*
  - 📡 Sonar Radar Ping *(Rhythmic pulse)*
  - 📁 Custom Upload *(Use any MP3 / WAV audio from your device)*
- 🚨 **Emergency Contacts & 1-Tap Dialing:** Quick call doctor, ambulance, or nearby pharmacy with instant phone dialer integration. Edit or remove emergency contacts anytime.
- 📶 **100% Offline & Standalone:** Runs completely offline on mobile using local database storage.

---

## 🚀 Running the Web Version Locally

If you wish to run the backend and web server on your computer:

### 1. Prerequisites
- Python 3.8 or higher installed.

### 2. Setup & Run
```bash
# Clone the repository
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>

# Install requirements
pip install -r requirements.txt

# Start the application server
python server.py
```
Open your browser at: **`http://localhost:5000`**

---

## 🛠️ Building the Native Android APK

The repository contains an automated build script:
```bash
build_android_apk.bat
```
This script syncs the web assets, compiles with Gradle (`assembleDebug`), and outputs the ready-to-use **`MedicineReminder.apk`**.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
