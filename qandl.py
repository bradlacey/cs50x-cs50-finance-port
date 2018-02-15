"""
      pass
      # return None

  try:
    # query QuandL for quote
    # https://blog.quandl.com/api-for-stock-data
      # try:
      # remember that f-strings need Python 3.6
      url = f"https://www.quandl.com/api/v3/datasets/EOD/"
      # url = "https://www.quandl.com/api/v3/datasets/EOD/"
      url += symbol
      url += ".csv?api_key=Yp6bSmznThD2mfDnUFyQ&column_index=1&rows=1"
      # full URL: https://www.quandl.com/api/v3/datasets/EOD/{{symbol}}.csv?api_key=Yp6bSmznThD2mfDnUFyQ&column_index=1&rows=1
      # e.g.:     https://www.quandl.com/api/v3/datasets/EOD/AAPL.csv?api_key=Yp6bSmznThD2mfDnUFyQ&column_index=1&rows=1

      request = "EOD/"
      request += symbol

      # shift 48 spaces to account for whitespace in data
      data_start = 48

      # ABOVE: TESTED

      # see documentation:
      # https://docs.quandl.com/docs/in-depth-usage

      # HERE: NEW

      # debugging:
      # working
      # return url

      with urllib.request.urlopen(url) as csvfile:
          results = csvfile.read()
          return type(results)
          for row in results:
              data += str(row)
      return apology(str(data))
      return {
          "name": data.upper(), # for backward compatibility with Yahoo
          "price": 0, # price,
          "symbol": data.upper()
      }
  except:
  """
