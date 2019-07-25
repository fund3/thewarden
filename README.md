# The WARden

*Version 0.10 Alpha*

__Found this project useful?__ \
_Consider tipping the developer: [tippin.me](https://tippin.me/@alphaazeta)_.

__Open Source License: [LICENSE](https://github.com/pxsocs/thewarden/blob/master/LICENSE)__\
__Contributing guidelines: [CONTRIBUTING.MD](https://github.com/pxsocs/thewarden/blob/master/CONTRIBUTING.md)__\
__Installation instructions: [INSTALL.MD](https://github.com/pxsocs/thewarden/blob/master/INSTALL.MD)__\
__Telegram group: [https://t.me/bitcoin_warden](https://t.me/bitcoin_warden)__

## Important Note for users upgrading from CryptoBlotter

The new version does not offer backward compatibility with previous versions. If you are running an older version and have transactions, make sure to __export the transactions as CSV and save them somewhere safe__. You can later import these into the new version. This is experimental and errors may occur. 

### Sample Portfolio View
All trades, bitcoin addresses and other information below are hypothetical only

![Front Page](https://github.com/pxsocs/thewarden/blob/master/thewarden/static/images/github_images/portfolio.png)

## About

The WARden is a portfolio tracking tool. It includes position monitoring and other analytics. One of the reasons that led me to develop this tool is to better manage cash inflows and outflows from digital positions while maintaining my data locally.

The app monitors daily _Net Asset Value (NAV)_. Similar to how a fund calculates performance. __So it's always tracking performance relative to current exposure.__

Furthermore, using my own node to verify and import transactions was a cumbersome process. By pairing with a __Samourai Dojo__, you can easily track addresses and import transactions from the blockchain while using your own full node. 

Telegram group: [https://t.me/bitcoin_warden](https://t.me/bitcoin_warden)

### Why NAV is important?

NAV is particularly important to anyone #stackingsats since it tracks performance relative to current capital allocated.
For example, a portfolio going from $100 to $200 may seem like it 2x but the performance really depends if any new capital was invested or divested during this period. __NAV adjusts for cash inflows and outflows.__

### Using a Bitcoin Full Node

You can now use a full node to monitor addresses and import transactions. This process is done using the Samourai Dojo platform. After researching the different options available, I decided the Dojo was best suited to integrate with the WARden. 

### Trade Pairs

The app is structured so that, by default, trades are included in pairs. This is similar to accounting entries where a credit and a debit are included as separate entries.
This is helpful so you can track your positions (assets) and your cash flows.
By doing this, it's easier to see how much fiat was deployed. It's particularly helpful in determining your historical average cost.
More info on how to import transactions can be found here: [CSV import details](http://www.thewarden.io/csvtemplate). You may also open the database and just paste the transactions.

Readme.1st

----------------------------;
**Please note that this is ALPHA software. There is no guarantee that the
information and analytics are correct. Also expect no customer support. Issues are encouraged to be raised through GitHub but they will be answered on a best efforts basis.**

All data is saved locally. __Consider a disk encryption__. Even though only public addresses and transactions are saved in the database, it's a good idea to password protect your computer and encrypt the hard drive containing the data. 

Any issues, suggestions or comments should be done at Github [ISSUES page](https://github.com/issues).


[Installation](https://github.com/pxsocs/thewarden/blob/master/INSTALL.MD) instructions

----------------------------;
Although Crypto Blotter can still be accessed at cryptoblotter.io, this will be discontinued soon. Users are expected to run this software locally. This option gives the user control over database (stored locally) and on whether or not to upgrade to new versions. 

[Click here](https://github.com/pxsocs/thewarden/blob/master/INSTALL.MD) for installation instructions.

Privacy
----------------------------;
Most portfolio tracking tools ask for personal information and may track your IP and other information. My experience is that even those who say they don't, may have log files at their systems that do track your IP and could be easily linked to your data.
_By cloning CB and running locally you reduce the risk of linkage of your IP, portfolio info and other information._

Asset and Liability tracking
----------------------------;
Different than most portfolio tracking tools, CB tracks both sides of transactions: _the crypto asset side and the fiat side._ This helps in analyzing cost basis, historical cash flows and fiat to crypto conversions along time.

NAV Tracking
----------------------------;
Another major difference is the concept of tracking Net Asset Value (NAV).
NAV tracks performance based on amount of capital allocated. For example, a portfolio starts at $100.00 on day 0. On day 1, there is a capital inflow of an additional $50.00. Now, if on day 2, the Portfolio value is $200, it's easy to conclude that there's a $50.00 profit. But in terms of % appreciation, there are different ways to calculate performance.
CB Calculates a daily NAV (starting at 100 on day zero).
In this example:

Day  | Portfolio Value*| Cash Flow  | NAV  | Performance |
-----|-----------------|------------|------|-------------|
0|$0.00|+ $100.00|100|--|
1|$110.00|+ $50.00 |110|+10.00% (1)|
2|$200.00|None|125|+25.00% (2)|

> * Portfolio Market Value at beginning of day
> (1) 10% = 110 / 100 - 1
> (2) 25% = 200 / (110 + 50) - 1

Tracking NAV is particularly helpful when #stackingsats. It calculates performance based on capital invested at any given time. A portfolio starting at $100 and ending at $200 at a given time frame, at first sight, may seem like is +100% but that depends entirely on amount of capital invested
along that time frame.

----------------------------;

## FAQ

### - Why include other Crypto Assets and not only Bitcoin?

We believe CB actually helps users realize the value of a Bitcoin only portfolio. But that's our opinion. We preferred to give users the ability to check their whole portfolio and provide them with the tools to assess how much better (or maybe worse) they would have been with a Bitcoin only portfolio.
Most crypto investors go through a period of investing in other assets. The quicker they realize this is a losing strategy, the better. We hope these tools help them learn quicker.

### - Why is NAV a better way to track a portfolio?

It takes into account deposits and withdraws. See table at NAV Tracking for more info.

### - Is there a mobile version available?

Not at this time.

### - Do I need to run it locally or is there a website I can use?

Cryptoblotter.io has a running copy of version 0.02 but will be discontinued soon.

### - On the remote version at cryptoblotter.io, what kind of information is gathered?

The debug.log file at the host we are using (Heroku) logs the IP addresses accessing the website. Also, username is stored at the database. __Use the website just for testing.__ We encourage users of the website to not use their real e-mail address (use a burner only for password recovery). __This software is designed to be ran locally at your machine.__

### - Why the DOJO and not other available options?

First and foremost, the Samourai team has shown continued support for open source. 
Second, our opinion is that they share values very similar to ours in terms of Bitcoin security and its future. 
Finally, the Dojo seemed like the best suited option for a fairly easy install and back-end integration with this project. 
