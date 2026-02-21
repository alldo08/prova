importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "AIzaSyCGkSCkznXVBanRx5gDgeVSRS2mJU90UT8",
    projectId: "projeto-web-app-16adb",
    messagingSenderId: "1011089630045",
    appId: "1:1011089630045:web:3afc16a9817f11409c7eb4"
});

const messaging = firebase.messaging();
