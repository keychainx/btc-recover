# *btcrecover* [![Build Status](https://travis-ci.org/gurnec/btcrecover.svg?branch=master)](https://travis-ci.org/gurnec/btcrecover) ![license](https://img.shields.io/badge/license-GPLv2-blue.svg) #

*btcrecover* is an open source Bitcoin wallet password and seed recovery tool. It is designed for the case where you already know most of your password or seed, but need assistance in trying different possible combinations.

## Features ##

 * Bitcoin wallet password recovery support for:
     * [Armory](https://bitcoinarmory.com/)
     * [Bitcoin Core (Bitcoin-Qt)](https://bitcoin.org/en/download)
     * [MultiBit Classic](https://multibit.org/) and [MultiBit HD](https://beta.multibit.org/)
     * [Electrum](https://electrum.org/) (1.x and 2.x)
     * Most wallets based on [bitcoinj](https://bitcoinj.github.io/), including [Hive for OS X](https://mac.hivewallet.com/)
     * BIP-39 passphrases (e.g. [TREZOR](https://www.bitcointrezor.com/) passphrases)
     * [mSIGNA (CoinVault)](https://ciphrex.com/products/)
     * [Blockchain.info](https://blockchain.info/wallet)
     * [pywallet --dumpwallet](https://github.com/jackjack-jj/pywallet) of Bitcoin Core wallets
     * [Bitcoin Wallet for Android/BlackBerry](https://play.google.com/store/apps/details?id=de.schildbach.wallet) spending PINs and encrypted backups
     * [KnC Wallet for Android](https://kncwallet.com/) encrypted backups
     * [Bither](https://bither.net/)
 * Altcoin password support for most wallets derived from one of those above, including:
     * [Litecoin-Qt](https://litecoin.org/)
     * [Electrum-LTC](https://electrum-ltc.org/)
     * [Litecoin Wallet for Android](https://litecoin.org/) encrypted backups
     * [Dogecoin Core](http://dogecoin.com/)
     * [MultiDoge](http://multidoge.org/)
     * [Dogecoin Wallet for Android](http://dogecoin.com/) encrypted backups
 * Bitcoin seed recovery support for:
     * [Electrum](https://electrum.org/) (1.x and 2.x, plus wallet file loading support)
     * BIP-32/39 compliant wallets ([bitcoinj](https://bitcoinj.github.io/)), including:
         * [MultiBit HD](https://beta.multibit.org/)
         * [Bitcoin Wallet for Android/BlackBerry](https://play.google.com/store/apps/details?id=de.schildbach.wallet) (with seeds previously extracted by [decrypt\_bitcoinj\_seeds](https://github.com/gurnec/decrypt_bitcoinj_seed))
         * [Hive for Android](https://play.google.com/store/apps/details?id=com.hivewallet.hive.cordova), [for iOS](https://itunes.apple.com/us/app/hive-wallet/id906990301), and [Hive Web](https://web.hivewallet.com/)
         * [breadwallet for iOS](https://itunes.apple.com/us/app/breadwallet-bitcoin-wallet/id885251393)
     * BIP-32/39/44 compliant wallets, including:
         * [Mycelium for Android](https://play.google.com/store/apps/details?id=com.mycelium.wallet)
         * [TREZOR](https://www.bitcointrezor.com/)
 * [Free and Open Source](http://en.wikipedia.org/wiki/Free_and_open-source_software) - anyone can download, inspect, use, and redistribute this software
 * Supported on Windows, Linux, and OS X
 * Support for Unicode passwords and seeds
 * Multithreaded searches, with user-selectable thread count
 * Experimental [GPU acceleration](docs/GPU_Acceleration.md) for Bitcoin Core, Armory, and derived altcoin wallets
 * Wildcard expansion for passwords
 * Typo simulation for passwords and seeds
 * Progress bar and ETA display (at the command line)
 * Optional autosave - interrupt and continue password recoveries without losing progress
 * Automated seed recovery with a simple graphical user interface
 * “Offline” mode for nearly all supported wallets - use one of the [extract scripts (click for more information)](docs/Extract_Scripts.md) to extract just enough information to attempt password recovery, without giving *btcrecover* or whoever runs it access to *any* of the addresses or private keys in your Bitcoin wallet.
 * “Nearly offline” mode for Armory - use an [extract script (click for more information)](docs/Extract_Scripts.md) to extract a single private key for attempting password recovery. *btcrecover* and whoever runs it will only have access to this one address/private key from your Bitcoin wallet (read the link above for an important caveat).

----------

### Documentation ###

**Please see the [Password Recovery Quick Start](TUTORIAL.md#btcrecover-tutorial) or the [Seed Recovery Quick Start](docs/Seedrecover_Quick_Start_Guide.md) for more information.**

If you find *btcrecover* helpful, please consider a small donation:
**[17LGpN2z62zp7RS825jXwYtE7zZ19Mxxu8](bitcoin:17LGpN2z62zp7RS825jXwYtE7zZ19Mxxu8?label=btcrecover)**

#### Thank You! ####
