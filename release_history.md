# Release History

## v.10 alpha

- Implemented TOR for anonymous requests
- Implemented TOR Status page and status bar display
- Included a check to see if TOR is running
- Included a page to check Dojo installation status + instructions
- Included Dojo status bar display
- Implemented method to read transactions from OXT using Tor
- Implemented Privacy Services Page
- Fixed an error on export CSV where folder was not being created (H/T: Nicholas)
- Fixed an error on export CSV where filename was not being generated (H/T: Nicholas)

## v.03 alpha (released on 7/1/2019)

- Fixed an issue where some charts were aggregating data when zoomed in
- Implemented new chart - average cost over time. Showing impact of transactions on average cost. 
- Created new error page when internet connection is not detected
- Fixed charts to have better scale on y Axis - better visibility
- Fixed an issue where debug.log size was not limited. Old files are now archived under `\debug_archive`.
- Included a new table on HeatMap page with a benchmark. Now portfolio performance can be compared to a benchmark.
- Included a handler for scalar errors as described in [issue #2](https://github.com/pxsocs/cryptoblotter/issues/2) 
- Implemented a new chart and table to calculate top drawdowns

## v.02 alpha (released on 6/22/2019)

- Fixed [issue #7](https://github.com/pxsocs/cryptoblotter/issues/7) that led to an error when a new portfolio is created and the first transaction was an __ASSET ONLY__ transaction.
- Related to [issue #7](https://github.com/pxsocs/cryptoblotter/issues/7) - fixed an issue with portfolios just created where return_1wk, etc would return error
- Included Portfolio Tooltips on Front Page (partial)
- Fixed [issue #4](https://github.com/pxsocs/cryptoblotter/issues/4) where Editing Transactions would default to BUY always
- Fixed [issue #6](https://github.com/pxsocs/cryptoblotter/issues/6) where debug.log file size was unlimited
- Fixed links at about.html page
- Fixed [issue #1](https://github.com/pxsocs/cryptoblotter/issues/1) - moved the block height request to blockstream.info.
- Fixed an issue on Portfolio_Compare where tickers that didn't have history that was long enough would return an error. Now, the performance of that ticker is zero (NAV is fixed at 100) until the date where data is available.
- Created Installation instructions for Windows users [issue #8](https://github.com/pxsocs/cryptoblotter/issues/8)
- Implemented a new view user /activity_summary (summary activity by ticker)
- Fixed sample.csv location (missed link)
- Fixed an issue with daily allocation position where % were calculated wrong
- Hide Breakevens that are too high (a small position left for example)
- Redesigned the Navigation Menu for a sidenav
- Included Attribution Chart
- Created Historical Allocation Chart
- Created new Scatter Plot Chart
