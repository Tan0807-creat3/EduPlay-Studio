# Security Policy (EduPlay Studio 1.0.0)

This document explains how to report security vulnerabilities related to EduPlay Studio.

## Scope

- Source code in this repository
- Installers and binaries built from this repository

## Secret management

- Do not commit API keys or tokens into the repository.
- EduPlay Studio uses Groq (OpenAI-compatible API). Store keys in environment variables:
  - `GROQ_API_KEY` or `EDUPLAY_GROQ_API_KEY`
- When sharing logs/screenshots, remove/obfuscate any secrets.

## Reporting a vulnerability

Please do not publicly disclose vulnerabilities before contacting the maintainers.

- Email: eduplay.line@hotmail.com

Include:
- OS + Python version
- EduPlay Studio version (1.0.0)
- Reproduction steps
- Any relevant logs (without secrets)
