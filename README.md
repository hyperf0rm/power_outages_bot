# ⚡️ Power Outages Bot

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)

A Telegram bot for monitoring power outages. The bot allows users to subscribe to notification alerts for specific addresses.

## 📋 Features

* ✅ **User Registration:** Saves user data upon first interaction.
* 🏠 **Address Management:** Users can add and remove addresses for tracking.
* 🔔 **Notifications:** Automatic alerts when outages are detected (via data parsing).
* 🐳 **Docker Support:** Full support for containerized deployment.
* 🔄 **CI/CD:** Automatic deployment via GitHub Actions (supports x86 and ARM64).

## 🛠 Tech Stack

* **Language:** Python 3.14+
* **Bot Framework:** [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)
* **Database:** PostgreSQL
* **DB Driver:** psycopg2-binary
* **Infrastructure:** Docker, Docker Compose
* **CI/CD:** GitHub Actions