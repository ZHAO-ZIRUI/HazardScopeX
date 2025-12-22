import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import MainView from './views/Main.vue'

const app = createApp(MainView)

app.use(createPinia())

app.mount('#app')
