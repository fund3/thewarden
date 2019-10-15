# Release History

## v.16 alpha

    - Fixed issues when importing Dojo addresses
    - Included button where user can force rescan of all Dojo addresses
    - Included balance of Bitcoin Addresses being monitored on dashboard
    - Implemented auto check of balances to detect changes and notify at dashboard
    - Fixed an issue where NAV was being calculated more often than needed
    - Redesign of layout
    - Redesign of dashboard
    - Included last 7 days overview at dashboard
    - Fixed issues with CSS tables not responsive on dashboard

## v.15 alpha (09/04/2019)

- Moved all JavaScript and CSS dependencies locally (Bootstrap, jQuery, Popper and others)
- Fixed reduntant js and css files
- Browser auto-launches at startup now
- Changed all file references to relative paths so app can be deployed
- Updated install instructions
- Built version now available for easy installation (Mac only for now)

## v.14 alpha (8/28/2019)

- Complete refactory of pricing feeds
- Support for multiple pricing APIs (currently CryptoCompare, Alphavantage and Bitmex)
- Included pricing model for easy inclusion of new APIs
- Included new page to test price feeds
- Enhanced calculations with new pricing requests
- With the new APIs, users can access pricing info since 2011 (compared to 2014 before)
- Fixed issues with drawdown calculation
- Fixed NAV calculation issues
- Included support for GBTC (realtime prices, history and premium calculation)
- Included GBTC premium on front page when position is present
- All API keys are now saved under a single file `/thewarden/pricing_engine/api_keys.conf` for easier key management
- Included new settings page to manage api keys and other 3rd party access variables
- Included a new popover on front page showing the full details for pnl calculations
- Included support for Financial Modeling Prep API (as a backup for stock prices)
- Dashboard now updates prices and positions in realtime
- Fixed an issue where some modals where not showing correctly
- Included details on how FIFO and LIFO unrealized cost is calculated
- Fixed issues in fx calculations
- Remodelled the 'Welcome' page.
- Remodelled the Front page to include login (cut extra step)
- Improved documentation of many functions
- Many bug fixes and improvements

## v.13 alpha (8/15/2019)

- Support to include trades in any fiat currency
- Realtime pricing of currencies + change base currency of portfolio.
- Fixed issues afecting NAV generation
- Fixed formatting issues
- Updated all charts to reflect currency selection
- NAV calculation includes impact of currency
- Optimized calculation intensive methods to remember recent values (memoization)

## v.12 alpha (released on 8/7/2019)

- Bug fixes and performance enhancements
- Included Import from Bitmex to import transactions
- Included pricing feed for Bitmex future contracts

## v.11 alpha (released on 8/3/2019)

- Many bug fixes and performance enhancements
- Fixed an issue with NAV generation
- Fixed an issue with new portfolios being imported from Dojo where NAV was not generated
- Fixed several issues with CSV imports and exports
- Fixed CSS formatting of several pages

## v.10 alpha (released on 7/23/2019)

- Implemented TOR for anonymous requests
- Implemented TOR Status page and status bar display
- Included a check to see if TOR is running
- Included a page to check Dojo installation status + instructions
- Included Dojo status bar display
- Implemented method to read transactions from OXT using Tor
- Implemented Privacy Services Page
- Fixed an error on export CSV where folder was not being created (H/T: Nicholas)
- Fixed an error on export CSV where filename was not being generated (H/T: Nicholas)
- New Dojo Features - import and monitor addresses
- Fixed pandas df errors (series vs dataframes)

## v.03 alpha (released on 7/1/2019)

- Fixed an issue where some charts were aggregating data when zoomed in
- Implemented new chart - average cost over time. Showing impact of transactions on average cost.
- Created new error page when internet connection is not detected
- Fixed charts to have better scale on y Axis - better visibility
- Fixed an issue where debug.log size was not limited. Old files are now archived under `\debug_archive`.
- Included a new table on HeatMap page with a benchmark. Now portfolio performance can be compared to a benchmark.
- Included a handler for scalar errors as described in [issue #2](https://github.com/pxsocs/thewarden/issues/2)
- Implemented a new chart and table to calculate top drawdowns

## v.02 alpha (released on 6/22/2019)

- Fixed [issue #7](https://github.com/pxsocs/thewarden/issues/7) that led to an error when a new portfolio is created and the first transaction was an **ASSET ONLY** transaction.
- Related to [issue #7](https://github.com/pxsocs/thewarden/issues/7) - fixed an issue with portfolios just created where return_1wk, etc would return error
- Included Portfolio Tooltips on Front Page (partial)
- Fixed [issue #4](https://github.com/pxsocs/thewarden/issues/4) where Editing Transactions would default to BUY always
- Fixed [issue #6](https://github.com/pxsocs/thewarden/issues/6) where debug.log file size was unlimited
- Fixed links at about.html page
- Fixed [issue #1](https://github.com/pxsocs/thewarden/issues/1) - moved the block height request to blockstream.info.
- Fixed an issue on Portfolio_Compare where tickers that didn't have history that was long enough would return an error. Now, the performance of that ticker is zero (NAV is fixed at 100) until the date where data is available.
- Created Installation instructions for Windows users [issue #8](https://github.com/pxsocs/thewarden/issues/8)
- Implemented a new view user /activity_summary (summary activity by ticker)
- Fixed sample.csv location (missed link)
- Fixed an issue with daily allocation position where % were calculated wrong
- Hide Breakevens that are too high (a small position left for example)
- Redesigned the Navigation Menu for a sidenav
- Included Attribution Chart
- Created Historical Allocation Chart
- Created new Scatter Plot Chart
