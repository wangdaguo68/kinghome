# 不想说

Flutter iOS/Android MVP for an AI emotion tree-hole app.

## Run Backend

Create `backend/.env` from `backend/.env.example` and set:

```env
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

Then run:

```powershell
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Run Flutter

The deployed backend is available at:

```text
http://39.106.115.87
```

Run with the deployed backend:

```powershell
D:\flutter35\flutter\bin\flutter.bat run
```

Android emulator can still use a local backend with `10.0.2.2`:

```powershell
D:\flutter35\flutter\bin\flutter.bat run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

For iOS simulator or desktop:

```powershell
D:\flutter35\flutter\bin\flutter.bat run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

For Android builds in China, set mirrors in the current PowerShell session:

```powershell
$env:FLUTTER_STORAGE_BASE_URL="https://storage.flutter-io.cn"
$env:PUB_HOSTED_URL="https://pub.flutter-io.cn"
$env:ANDROID_HOME="D:\Android"
$env:JAVA_HOME="C:\Program Files\Android\openjdk\jdk-21.0.8"
cd android
.\gradlew.bat :app:assembleDebug
```

## Checks

```powershell
python -m pytest
D:\flutter35\flutter\bin\flutter.bat analyze
D:\flutter35\flutter\bin\flutter.bat test
```

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Lab: Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Cookbook: Useful Flutter samples](https://docs.flutter.dev/cookbook)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.
