// Frida скрипт для перехвата идентификаторов
Java.perform(function() {
    console.log("[*] Frida hooks started");

    // 1. IMEI / MEID
    try {
        var TelephonyManager = Java.use("android.telephony.TelephonyManager");
        TelephonyManager.getDeviceId.implementation = function() {
            var result = this.getDeviceId();
            console.log("[IMEI] " + result);
            return result;
        };
        TelephonyManager.getImei.implementation = function() {
            var result = this.getImei();
            console.log("[IMEI] " + result);
            return result;
        };
        console.log("[+] Hooked IMEI");
    } catch(e) {}

    // 2. Android ID
    try {
        var Settings = Java.use("android.provider.Settings$Secure");
        Settings.getString.implementation = function(resolver, name) {
            var result = this.getString(resolver, name);
            if (name && name.indexOf("android_id") !== -1) {
                console.log("[ANDROID_ID] " + result);
            }
            return result;
        };
        console.log("[+] Hooked Android ID");
    } catch(e) {}

    // 3. MAC Address
    try {
        var WifiInfo = Java.use("android.net.wifi.WifiInfo");
        WifiInfo.getMacAddress.implementation = function() {
            var result = this.getMacAddress();
            console.log("[MAC] " + result);
            return result;
        };
        console.log("[+] Hooked MAC");
    } catch(e) {}

    // 4. IMSI
    try {
        var TelephonyManager = Java.use("android.telephony.TelephonyManager");
        TelephonyManager.getSubscriberId.implementation = function() {
            var result = this.getSubscriberId();
            console.log("[IMSI] " + result);
            return result;
        };
        console.log("[+] Hooked IMSI");
    } catch(e) {}

    // 5. Serial Number
    try {
        var Build = Java.use("android.os.Build");
        Build.getSerial.implementation = function() {
            var result = this.getSerial();
            console.log("[SERIAL] " + result);
            return result;
        };
        console.log("[+] Hooked Serial");
    } catch(e) {}

    // 6. Phone Number
    try {
        var TelephonyManager = Java.use("android.telephony.TelephonyManager");
        TelephonyManager.getLine1Number.implementation = function() {
            var result = this.getLine1Number();
            console.log("[PHONE] " + result);
            return result;
        };
        console.log("[+] Hooked Phone Number");
    } catch(e) {}

    console.log("[*] All hooks installed");
});