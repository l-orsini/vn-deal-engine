# VN Deal Engine

Personal learning project (Python, web APIs): find highly rated visual
novels that are sold on Steam, track their price history, and estimate
when the next sale will happen.

## The idea

- **VNDB** is the community reference for visual novel ratings and
  votes, but does not provide prices.
- **Steam** provides prices and discounts, accessed through the
  **IsThereAnyDeal (ITAD)** API, which also keeps the price history.

The project links them using the `steam_appid`, an identifier extracted
from VNDB's external links, then converted to an ITAD id. I do not match
titles, as that would be too fragile (romanized titles, Japanese titles,
subtitles).

## Project status

- [x] Query to the VNDB Kana API with server-side filters (rating, votes, releases)
- [x] SFW filter on releases (`minage < 18` for the VN list, `has_ero != 1` for the release lookup) instead of the cover image
- [x] Steam appid extraction with a regular expression
- [x] Finding the appid through the VN's releases (one extra request per VN)
- [x] Steam appid → ITAD id conversion
- [x] Fetching current prices (ITAD, Steam shop, country `FR` by default)
- [x] Fetching full price history (since 2011)
- [x] SQLite database (`vn.db`): `vn` and `price_history` tables
- [x] Cache: a VN is only refreshed if its data is older than a given delay
- [x] Next sale estimation: median of the gaps between sales
- [ ] Improve next-sale prediction with scikit-learn (replace the median of gaps with a trained model)
- [ ] Cardview interface, with a "Show price" button
- [ ] Make the filters (rating, votes) adjustable by the user

## How it works

1. `load_n_vns(n)`: asks VNDB for the `n` most voted VNs matching the
   filters (rating, votes, at least one SFW Steam release).
2. `vnid_to_steamid()`: queries the VN's releases to extract the Steam appid.
3. `steam_to_itad_id()`: converts the appid to an ITAD id.
4. `itad_price()` / `price_history()`: fetch the current price and the history.
5. `refresh_vns()`: orchestrates everything and saves to SQLite,
   skipping VNs that are still fresh (`is_fresh()`).
6. `estimate_next_sale()`: computes the gaps between the end of one sale
   and the start of the next, takes the median, and adds it to the last
   known date. Returns `None` if there are fewer than 10 gaps (not
   enough data, or free game).

## Configuration

Create a `.env` file at the project root:

```
ITAD_API_KEY=your_key_here
```

## Running the script

```bash
pip install requests python-dotenv
python vndeal.py
```

## Technical choices

- **Sorting by vote count** rather than rating: a high rating with few
  votes is unreliable.
- **Server-side filters** (`filters`) to select VNs, and `fields` to
  choose which data is returned.
- **Steam links live on releases, not on VNs**: VNDB can filter VNs by
  their releases but cannot return release data in the same request,
  hence a second request per VN.
- **Prices stored as integers** (`amountInt`, in cents) to avoid
  floating-point errors.
- **Median instead of mean** for sale gaps: robust to rare, very long
  periods without sales.
- **`INSERT OR IGNORE`** on price history, so refreshes never create duplicates.

## Known limitations: reliability of the median estimate

- Steam sales follow the calendar (Winter sale, Summer sale...), not a regular rhythm, so the median can give a date when nothing usually happens.
- The estimate starts from the last price change, not from the end of the last sale, so the predicted date can be wrong or already past.
- Old sales count as much as recent ones, and the result is a single date with no margin of error.
- With few sales in the history, one new sale can shift the result a lot.
- The median stays useful as a baseline to compare against scikit-learn.

## Technologies

Python 3, `requests`, `python-dotenv`, `sqlite3`, `re` (regular
expressions), web APIs (VNDB Kana, IsThereAnyDeal) and JSON.
