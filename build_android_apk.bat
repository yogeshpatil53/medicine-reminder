@echo off
title MedRemind - Android APK Builder
echo ========================================================
echo   Building MedRemind Native Android APK...
echo ========================================================
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "PATH=%JAVA_HOME%\bin;%PATH%"

echo 1. Syncing latest web app assets...
xcopy /s /y "static\*" "C:\Users\ALG GAMING\AndroidStudioProjects\medicinereminder\app\src\main\assets\"

echo 2. Compiling Android APK with Gradle...
cd /d "C:\Users\ALG GAMING\AndroidStudioProjects\medicinereminder"
call gradlew.bat assembleDebug

echo 3. Copying APK to Medicine Reminder folder...
copy /y "app\build\outputs\apk\debug\app-debug.apk" "c:\Medicine Reminder\MedicineReminder.apk"

echo ========================================================
echo   BUILD COMPLETE!
echo   Output: c:\Medicine Reminder\MedicineReminder.apk
echo ========================================================
pause
