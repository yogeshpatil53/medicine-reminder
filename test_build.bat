@echo off
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "PATH=%JAVA_HOME%\bin;%PATH%"
cd /d "C:\Users\ALG GAMING\AndroidStudioProjects\medicinereminder"
call gradlew.bat assembleDebug
