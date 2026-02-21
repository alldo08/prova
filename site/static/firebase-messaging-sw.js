// static/firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

const firebaseConfig = {
    apiKey: "AIzaSyCGkSCkznXVBanRx5gDgeVSRS2mJU90UT8",
    projectId: "projeto-web-app-16adb",
    messagingSenderId: "1011089630045",
    appId: "1:1011089630045:web:3afc16a9817f11409c7eb4"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

// Captura notificações quando o app está fechado
messaging.onBackgroundMessage((payload) => {
    console.log('Mensagem em segundo plano:', payload);
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: '/static/logo.png' // certifique-se que este ícone existe
    };
    self.registration.showNotification(notificationTitle, notificationOptions);
});
