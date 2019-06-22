# Release History

## v.02 alpha

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
