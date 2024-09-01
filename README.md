# Flask_

## 🌟 Highlights

### Run
```bash
flask --app  manage.py test --coverage
```

## ℹ️ Overview

This is a learning project based on the Flask framework, which is a simple web application for a blog.

## ⬇️ Installation

Simple, understandable installation instructions

```bash
pip install -r requirements.txt
```
Warning! Webdriver for Chrome-browser should has actual version.

### DB commands:
  ```bash
  $ flask db stamp head
  $ flask db migrate
  $ flask db upgrade
```
### Profiler 
To get the profile code for each function according to their speed.
Len 25 is the number of the slowest functions in the output.

### .env
The FLASK_COVERAGE value and parameters are specified in config.py or by default.
