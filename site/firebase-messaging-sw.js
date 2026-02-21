// firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "AIzaSyCGkSCkznXVBanRx5gDgeVSRS2mJU90UT8",
    projectId: "projeto-web-app-16adb",
    messagingSenderId: "1011089630045",
    appId: "1:1011089630045:web:3afc16a9817f11409c7eb4"
});

const messaging = firebase.messaging();

// Opcional: Tratar mensagens em segundo plano
messaging.onBackgroundMessage((payload) => {
    console.log('Mensagem recebida em segundo plano:', payload);
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: '/static/icon.png'
    };
    self.registration.showNotification(notificationTitle, notificationOptions);
});
