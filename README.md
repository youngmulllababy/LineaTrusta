# LineaTrusta

## Overview

Pass trusta humanity & media attestation for Linea.

## Requirements

- Python 3.11

## Getting Started

1. **Set Up Your Private Keys**

   - In the file named `private_keys.txt` insert your EVM private keys with each key on a separate line.

2. **Set Up Your Twitter Tokens**

   - In the file named `tokens.txt` insert your twitter tokens with each token on a separate line.

3. **Set Up Your Proxy**

   - In the file named `proxies.txt` insert your proxy using this format: `user:pass@ip:port`

4. **Configure the Application**

   - Open the `settings.py` file in the project directory.
   - You can configure:
     - Linea max gwei
     - Sleep between transactions
     - Attestation types

## Abilities

- Waits for desired Linea gwei and perform the transaction in low gas
- Creates report at the end of the run indicating which accounts passed and which failed
- Will not do on chain transaction if already did

## Running the Application


```bash
pip install -r requirements 
python main.py
```
