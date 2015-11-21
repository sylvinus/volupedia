from flask import Flask, send_from_directory, request
import requests
import json
import urllib
import lxml
import lxml.html
import re
import os


app = Flask(__name__, static_url_path='/__static', static_folder='static')


# Make sure we don't get indexed at all!
@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):

  wp_url = "http://en.wikipedia.org/%s" % path
  if request.query_string:
    wp_url += "?%s" % request.query_string

  print "Wikipedia URL: ", wp_url

  wp_req = requests.get(wp_url)

  # TODO: also send headers along!
  if "text/html" not in wp_req.headers.get('Content-Type', ""):
    return wp_req.content

  tree = lxml.html.fromstring(wp_req.content)

  # Find which images we want to replace
  wp_images = tree.cssselect("table.infobox img, .thumb.tright img")
  title_elt = tree.cssselect("h1")

  if len(title_elt) and len(wp_images):
    title = (re.sub("<.*?>", "", lxml.html.tostring(title_elt[0])) or "").strip()

    print "Title: ", title

    if title:
      models = list(search_sketchfab_models(title))
      if len(models):

        width = wp_images[0].attrib.get("width", 290)
        height = int(int(width) * 1.3)  # wp_images[0].attrib.get("height", 190)
        embed_html = str(get_sketchfab_embed(models[0]["uid"], width=width, height=height))

        # Replace the first image we find with the first sketchfab embed
        wp_images[0].getparent().replace(wp_images[0], lxml.html.fromstring(embed_html))

  return lxml.html.tostring(tree)


def get_sketchfab_embed(sketchfab_id, width=640, height=480):

  html = '<iframe width="%s" height="%s" src="https://sketchfab.com/models/%s/embed" frameborder="0" allowfullscreen mozallowfullscreen="true" webkitallowfullscreen="true" onmousewheel=""></iframe>' % (
    width, height, sketchfab_id
  )

  return html


def search_sketchfab_models(search):
  api_url = "https://sketchfab.com/i/models?count=24&amp;features=&amp;flag=&amp;offset=0&amp;search=%s&amp;sort_by=-likeCount" % urllib.quote(search.encode("utf-8"))
  js = json.loads(requests.get(api_url).content)

  for res in js.get("results"):
    yield res

# Run the app!
port = int(os.environ.get("PORT", 5000))
app.run(host='0.0.0.0', port=port)
