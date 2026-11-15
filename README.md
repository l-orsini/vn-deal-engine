# VN Deal Engine

Personal learning project (Python, web APIs): find highly rated visual
novels that are sold on Steam, with the goal of eventually spotting
which ones are on sale.

## The idea

- **VNDB** is the community reference for visual novel ratings and
  votes, but does not provide prices.
- **Steam** provides prices and discounts.

The project links the two using the `steam_appid`, an identifier shared
by both, extracted from VNDB's external links. I do not match titles,
as that would be too fragile (romanized titles, Japanese titles,
subtitles).

## Project status

- [x] Query to the VNDB Kana API with filters (rating, votes, releases)
- [x] Cover image filter to exclude NSFW content
- [x] Steam appid extraction with a regular expression, with tests
- [ ] Finding the appid through releases (in progress)
- [ ] Fetching prices
- [ ] Streamlit card interface, with a "Show price" button
- [ ] SQLite database and price history

**Known limitation:** Steam links are attached to a visual novel's
*releases*, not to the visual novel itself. For now, `vndeal.py`
searches the VN's own links and therefore prints `None` for the appid.
An extra request per VN, on its releases, is needed and will be the
next step.

## Running the script

```bash
pip install requests
python vndeal.py
```

## Technical choices

- **Sorting by vote count** rather than rating: a high rating with few
  votes is unreliable.
- **Server-side filters** (`filters`) to select VNs, and `fields` to
  choose which data is returned.
- **Cover image alone is not enough** to filter adult content: the
  releases' `has_ero` field is planned for later.

## Technologies

Python 3, `requests`, `re` (regular expressions), web APIs and JSON.
