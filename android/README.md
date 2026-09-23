# Android wrapper for SportStream mobile

This folder contains a minimal Android Studio wrapper for the current Django app.

## How to use

1. Open Android Studio.
2. Create a new project with "Empty Activity".
3. Copy the files in this folder into the new project structure.
4. Update the package name if needed.
5. Replace the default URL in `MainActivity.kt` with your production app URL.
6. Build the APK/AAB.

## Default behavior

- Loads the web app inside a `WebView`
- Enables JavaScript
- Allows navigation using the back button
- Uses Internet permission to fetch the website data
