<div align="center">
  <img src="logo.png" alt="Repeater Organizer Logo" width="200"/>
  <h1>Repeater Organizer</h1>
  <p>A powerful Burp Suite extension to automatically name and organize your Repeater tabs.</p>
  
  [**🇺🇸 English**](README.md) | [**🇮🇷 فارسی**](README-fa.md)
</div>

---

## 🌍 About

Repeater Organizer is a Burp Suite extension written in Python (Jython) that automatically manages and renames your Repeater tabs based on the contents of the HTTP request. Say goodbye to the endless sea of numbered tabs (1, 2, 3...) and instantly identify requests by their Method, Host, Path, and Query parameters.

---

## ✨ Features

- 🔄 **Background Auto-Naming:** Automatically renames new tabs in the background as soon as you send a request to Repeater (e.g., using `CTRL+R`).
- 🧠 **Smart Naming Engine:** Intelligently extracts the optimal path from your request and safely truncates long strings.
- ⚙️ **Smart Options:** 
  - `Include [HOST] Prefix`: Adds the target domain.
  - `Include Method Prefix`: Adds the HTTP method.
  - `Include Query Params`: Appends the query string.
- 🛠️ **Custom Format Engine:** Total control over tab names using dynamic variables (e.g., `[{method}] {host}{path}{path}`).
- 🗂️ **Organize Existing Tabs:** One-click batch renaming for all your currently open tabs.
- ⏪ **Reset to Numbers:** Safely revert all tabs back to their default numbered state.

---

## 📸 Screenshots

<div align="center">
  <img src="screenshot1.png" alt="Smart Naming Configuration" width="600"/>
  <br>
  <i>Smart Naming Configuration UI</i>
</div>

<br>

<div align="center">
  <img src="screenshot2.png" alt="Custom Format Engine" width="600"/>
  <br>
  <i>Custom Format Engine in Action</i>
</div>

---

## 🚀 Installation

1. Download [Jython Standalone JAR](https://www.jython.org/download) and add it to your Burp Suite (`Extender` -> `Options` -> `Python Environment`).
2. Download the `repeater_organizer.py` script from this repository.
3. In Burp Suite, go to the `Extender` -> `Extensions` tab.
4. Click `Add`, choose `Extension Type: Python`, and select the `repeater_organizer.py` file.
5. The **Repeater Organizer** tab will appear in your Burp Suite UI.

---

## 🛠️ Usage & Variables

### Custom Format Variables
When using the **Custom Format Engine**, you can build your own naming templates using the following variables:

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{method}` | HTTP Method | `GET`, `POST` |
| `{host}` | Target Domain | `api.target.com` |
| `{fullpath}` | Complete URL path | `/v1/users/create` |
| `{path}` | A path segment. Stack them! | `{path}{path}` &rarr; `users/create` |
| `{endpoint}` | The very last segment | `create` |
| `{query}` | The query string | `?id=123` |

**Format Examples:**
- `[{method}] {host}{path}{path}` &rarr; `[POST] api.target.com/v1/users`
- `{endpoint}{query} ({method})` &rarr; `users?id=123 (POST)`

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!

## 📄 License
This project is licensed under the MIT License.
