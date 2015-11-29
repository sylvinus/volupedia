from flask import Flask, send_from_directory, request, redirect
import requests
import json
import urllib
import lxml
import lxml.html
import re
import os
from urlparse import urlparse, urlunparse


app = Flask(__name__, static_url_path='/__static', static_folder='static')


@app.before_request
def redirect_nonwww():
    """ Make sure we use the right domain. TODO: lang detection! """

    urlparts = urlparse(request.url)
    if "volupedia" in urlparts.netloc and urlparts.netloc != "en.volupedia.org":
        urlparts_list = list(urlparts)
        urlparts_list[1] = 'en.volupedia.org'
        return redirect(urlunparse(urlparts_list), code=301)


# Make sure we don't get indexed at all!
@app.route('/robots.txt')
@app.route('/static/images/project-logos/enwiki-2x.png')
@app.route('/static/images/project-logos/enwiki-1.5x.png')
@app.route('/static/images/project-logos/enwiki.png')
def static_from_root():
    return send_from_directory(app.static_folder, os.path.basename(request.path[1:]))


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):

  wp_url = "https://en.wikipedia.org/%s" % path
  if request.query_string:
    wp_url += "?%s" % request.query_string

  print "Wikipedia URL: ", wp_url

  wp_req = requests.get(wp_url, allow_redirects=False)

  # Intercept redirects (mostly after search)
  if wp_req.headers.get("location"):
    urlparts = list(urlparse(wp_req.headers["location"]))
    req_urlparts = list(urlparse(request.url))
    urlparts[0] = req_urlparts[0]
    urlparts[1] = req_urlparts[1]
    return redirect(urlunparse(urlparts), code=wp_req.status_code)

  # TODO: also send headers along!
  if "text/html" not in wp_req.headers.get('Content-Type', ""):
    return wp_req.content

  tree = lxml.html.fromstring(wp_req.content)

  inserter = InfoboxInserter(tree)
  if not inserter.exists():
    inserter = ThumbInserter(tree)

  title_elt = tree.cssselect("h1")
  body_elt = tree.cssselect("body")

  if len(title_elt) and inserter.exists():
    title = (re.sub("<.*?>", "", lxml.html.tostring(title_elt[0])) or "").strip()

    print "Title: ", title

    if title:
      models = list(search_sketchfab_models(title))
      print models
      if len(models):

        width = inserter.get_width()
        height = int(int(width) * 1.3)  # wp_images[0].attrib.get("height", 190)
        embed_html = str(get_sketchfab_embed(models[0], width=width, height=height))

        inserter.insert(embed_html)

  # Insert disclaimer banner
  body_elt[0].insert(0, lxml.html.fromstring("""
    <div style="font-size:14px;height:28px;width:100%;background-color:#FDF2AB;border-bottom:1px solid #CCC;position:absolute;top:-28px;">
      <div style="padding:6px;">
        Volupedia is an experiment mixing <a href="https://www.wikipedia.org/">Wikipedia</a> pages with 3D models from <a href="http://www.sketchfab.com">Sketchfab</a>. Code &amp; feedback on <a href="https://github.com/sylvinus/volupedia">GitHub</a>!
        <a style="float:right;" href="https://donate.wikimedia.org/">Donate to Wikipedia</a>
      </div>
    </div>
  """))
  body_elt[0].attrib["style"] = "position:relative;top:28px;"

  return lxml.html.tostring(tree)


class InfoboxInserter(object):
  def __init__(self, tree):
    self.tree = tree

  def exists(self):
    return len(self.tree.cssselect("table.infobox td")) > 0

  def get_width(self):
    wp_infobox = self.tree.cssselect("table.infobox")
    wp_infobox_style_width = re.search("width\s*\:\s*([0-9]+)px", wp_infobox[0].attrib.get("style", ""))
    width = wp_infobox[0].attrib.get("width", int(wp_infobox_style_width.group(1)) if wp_infobox_style_width else 290)
    return width

  def insert(self, embed_html):
    wp_infobox_td = self.tree.cssselect("table.infobox td")
    wp_infobox_td[0].insert(0, lxml.html.fromstring(embed_html + "<br/>"))


class ThumbInserter(InfoboxInserter):
  def exists(self):
    self.inner = self.tree.cssselect(".thumb.tright .thumbinner")
    return len(self.inner) > 0

  def get_width(self):
    style_width = re.search("width\s*\:\s*([0-9]+)px", self.inner[0].attrib.get("style", ""))
    if style_width:
      return int(style_width.group(1)) - 2
    else:
      return 220

  def insert(self, embed_html):
    for child in self.inner[0].getchildren():
      self.inner[0].remove(child)
    self.inner[0].insert(0, lxml.html.fromstring(embed_html))


def get_sketchfab_embed(sketchfab_model, width=640, height=480):

  html = '<iframe width="%s" height="%s" src="https://sketchfab.com/models/%s/embed" frameborder="0" allowfullscreen mozallowfullscreen="true" webkitallowfullscreen="true" onmousewheel=""></iframe><div style="text-align:center;">"%s" by <a href="https://sketchfab.com/%s">%s</a></div>' % (
    width, height, sketchfab_model["uid"], sketchfab_model.get("name", "Unknown"), sketchfab_model["user"]["username"], sketchfab_model["user"]["displayName"]
  )

  return html


def search_sketchfab_models(search):
  api_url = "https://sketchfab.com/i/models?count=24&features=&flag=&offset=0&search=%s&sort_by=-likeCount" % urllib.quote(search.encode("utf-8"))
  js = json.loads(requests.get(api_url).content)

  for res in js.get("results"):
    yield res


# Run the app!
if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  debug = bool(os.environ.get("DEBUG"))
  app.run(host='0.0.0.0', port=port, debug=debug)
