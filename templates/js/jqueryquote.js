// source: CS50 Ajax Short
function ajax_request(argument)
{
    var aj = new XMLHttpRequest();
    aj.onreadystatechange = function() {
        if (aj.readyState == 4 && aj.status == 200)
        // do something to the page
    };
    
    aj.open("GET", /* url */, true);
    aj.send();
}

// source: CS50 Ajax Short
// create another special new Javascript object called an XMLHttpRequest
var xhttp = new XMLHttpRequest();

// codify the state of being when we visit a page
var onreadystatechange = false;

// XMLHttpRequest has two additional properties:
// - readyState (it will change from 0--request not yet initalised--to 1
// , 2, 3, and 4--request finished, response ready.)
// - status (hopefully it will be 200--okay)

// then just make our asynchronous request using the open() method to
// define the request and the send() method to actually send it

if (XMLHttpRequest.readyState != 4 || XMLHttpRequest.status != 200) {
    // that's bad
}


// source: CS50 DOM Short
$(document).ready(function() {
    $('.jQButton').click(function() {
        $('#colorDiv').css('background-color', this.innerHTML.toLowerCase());
    });
});


# GET CSV
url = f"https://www.alphavantage.co/query?apikey=NAJXWIA8D6VN6A3K&datatype=csv&function=TIME_SERIES_INTRADAY&interval=1min&symbol={symbol}"
webpage = urllib.request.urlopen(url)

# parse CSV
datareader = csv.reader(webpage.read().decode("utf-8").splitlines())

# ignore first row
next(datareader)

# parse second row
row = next(datareader)

# ensure stock exists
try:
    price = float(row[4])
except:
    return None

# return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
return {
    "name": symbol.upper(), # for backward compatibility with Yahoo
    "price": price,
    "symbol": symbol.upper()
}