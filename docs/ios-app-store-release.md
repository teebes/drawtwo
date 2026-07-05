# iOS App Store Release Checklist

Use this when uploading a new DrawTwo iOS build from Xcode.

## Project

- Xcode project: `ios/Archetype/Archetype.xcodeproj`
- Scheme/target: `Archetype`
- Release bundle ID: `com.morelsoft.drawtwo`
- Debug bundle ID: `com.morelsoft.drawtwo.dev`
- Signing team: Morelsoft developer team, currently `X84Q7QHUZJ`

## Before Xcode

1. Make sure the release code is merged and the production backend is ready for
   any API changes the app needs.
2. Run the normal local checks, at least `make ci-check` when practical.
3. Confirm App Store Connect has an app record for `com.morelsoft.drawtwo`.
   First-time or major releases also need screenshots, app privacy, age rating,
   review notes, and release notes prepared in App Store Connect.

## Xcode Steps

1. Open `ios/Archetype/Archetype.xcodeproj`.
2. Select the `Archetype` target, then check `Signing & Capabilities`.
   - Use the Morelsoft team.
   - Use automatic signing unless there is a specific reason not to.
   - Confirm the Release bundle ID is `com.morelsoft.drawtwo`.
   - Resolve any signing, capability, or entitlement warnings before archiving.
3. Select the `Archetype` target, then check `General > Identity`.
   - `Version` is the public App Store version (`MARKETING_VERSION`).
   - `Build` is the upload/build number (`CURRENT_PROJECT_VERSION`).
   - Increment `Build` before every App Store Connect upload.
   - Increment `Version` only when creating a new App Store version. If you are
     replacing a rejected or broken upload for the same version, keep `Version`
     the same and only increment `Build`.
4. In the scheme/device selector, choose `Archetype` and a generic or physical
   iOS device, not a simulator. Xcode cannot create an App Store archive for a
   simulator destination.
5. Choose `Product > Archive`.
6. In Organizer, select the new archive and click `Validate App`. Fix any
   validation errors.
7. Click `Distribute App`.
   - Distribution method: `App Store Connect`
   - Destination: `Upload`
   - Signing: automatic
   - Keep debug symbols/dSYMs included unless there is a specific reason not to.
8. Upload and wait for Apple processing. The build will appear in App Store
   Connect after processing completes.

## App Store Connect Steps

1. Open the app in App Store Connect.
2. Create or select the iOS version that matches the Xcode `Version`.
3. Attach the processed build.
4. Complete release notes, screenshots, review info, app privacy, age rating,
   and export compliance.
5. Submit for App Review.
6. After approval, release manually or let the configured release option publish
   it automatically.

## Notes

- The uploaded build is matched to App Store Connect by bundle ID and version;
  the build number uniquely identifies each upload.
- `ios/Archetype/Archetype/Info.plist` already sets
  `ITSAppUsesNonExemptEncryption` to `false`.
- The same uploaded build can be used for TestFlight before App Review.
- Current Release settings in the project are `MARKETING_VERSION = 1.0.1` and
  `CURRENT_PROJECT_VERSION = 2`; update these in Xcode for the next upload.

## References

- Apple: Upload builds:
  https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/
- Apple: Create a new version:
  https://developer.apple.com/help/app-store-connect/update-your-app/create-a-new-version/
- Apple Xcode Help: Prepare for app distribution:
  https://help.apple.com/xcode/mac/current/en.lproj/dev91fe7130a.html
- Apple Xcode Help: Create an archive:
  https://help.apple.com/xcode/mac/current/en.lproj/devf37a1db04.html
- Apple Xcode Help: Upload an app to App Store Connect:
  https://help.apple.com/xcode/mac/current/en.lproj/dev442d7f2ca.html
