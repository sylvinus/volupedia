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
    return redirect(replace_domain(request.url, "http://en.volupedia.org", protocol=False), code=301)


@app.route('/robots.txt')  # Make sure we don't get indexed at all!
@app.route('/static/images/project-logos/enwiki-2x.png')  # replace logo by our own
@app.route('/static/images/project-logos/enwiki-1.5x.png')
@app.route('/static/images/project-logos/enwiki.png')
def static_from_root():
  return send_from_directory(app.static_folder, os.path.basename(request.path[1:]))


# All other requests will go through this handler
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):

  wp_url = replace_domain(request.url, "https://en.wikipedia.org/", protocol=True)

  # Reverse request to Wikipedia
  wp_req = requests.get(wp_url, allow_redirects=False)

  # Intercept redirects (mostly after search)
  if wp_req.headers.get("location"):
    return redirect(replace_domain(wp_req.headers["location"], request.url, protocol=True), code=wp_req.status_code)

  # We do a straight reverse proxy for everything other than HTML
  # TODO: also send headers along!
  if "text/html" not in wp_req.headers.get('Content-Type', ""):

    # if "mediawiki&only=script" in wp_url:
    #   return wp_req.content + "mw.centralNotice.insertBanner = function() {};"

    # Hacky way to disable BannerLoader, which conflicts with our own banner. We have a permanent donate link in ours.
    if "modules=startup" in wp_url:
      return wp_req.content.replace("//meta.wikimedia.org/w/index.php?title=Special:BannerLoader", "#")

    return wp_req.content

  tree = lxml.html.fromstring(wp_req.content)

  inserter = InfoboxInserter(tree)
  if not inserter.exists():
    inserter = ThumbInserter(tree)

  title_elt = tree.cssselect("h1")
  body_elt = tree.cssselect("body")

  if len(title_elt) and inserter.exists():
    title = (re.sub("<.*?>", "", lxml.html.tostring(title_elt[0])) or "").strip()

    if title:
      models = list(search_sketchfab_models(title))

      # Only replace if we found a page title, somewhere to insert, and a matching Sketchfab model!
      if len(models):

        width = inserter.get_width()
        height = int(int(width) * 1.3)  # wp_images[0].attrib.get("height", 190)
        embed_html = unicode(get_sketchfab_embed(models[0], width=width, height=height))

        inserter.insert(embed_html)

  random_pages = """
http://en.volupedia.org/wiki/Tesla_Motors
http://en.volupedia.org/wiki/Rio_de_Janeiro
http://en.volupedia.org/wiki/Samsung
http://en.volupedia.org/wiki/Solar_Impulse
http://en.volupedia.org/wiki/British_Museum
http://en.volupedia.org/wiki/Kathmandu
http://en.volupedia.org/wiki/Barack_Obama
http://en.volupedia.org/wiki/Solar_System
http://en.volupedia.org/wiki/NEAR_Shoemaker
http://en.volupedia.org/wiki/Stegosaurus
http://en.volupedia.org/wiki/Moai
http://en.volupedia.org/wiki/Minecraft
http://en.volupedia.org/wiki/Yoda
http://en.volupedia.org/wiki/Dwayne_Johnson
""".strip().split("\n")

  # Insert disclaimer banner
  body_elt[0].insert(0, lxml.html.fromstring("""
    <div style="font-size:14px;height:28px;width:100%%;background-color:#FDF2AB;border-bottom:1px solid #CCC;position:absolute;top:-28px;overflow:hidden;line-height:28px;">
      <div style="padding:0px 6px 0px 6px;">
        Volupedia is an experiment mixing <a href="https://www.wikipedia.org/">Wikipedia</a> pages with 3D models from <a href="http://www.sketchfab.com">Sketchfab</a>.
        <a href="#" onclick='window.location=%s[parseInt(Math.random()*%s, 10)]; return false;'>Random example</a>.

        <div style="float:right;">
          Code &amp; feedback on <a href="https://github.com/sylvinus/volupedia">GitHub</a>.
          <a href="https://donate.wikimedia.org/">Donate to Wikipedia</a>!
        </div>


        <div style="float:right;margin:4px 10px 0px 0px;">

          <!-- Load Facebook SDK for JavaScript -->
          <div id="fb-root"></div>
          <script>(function(d, s, id) {
            var js, fjs = d.getElementsByTagName(s)[0];
            if (d.getElementById(id)) return;
            js = d.createElement(s); js.id = id;
            js.src = "//connect.facebook.net/en_US/sdk.js#xfbml=1&version=v2.0";
            fjs.parentNode.insertBefore(js, fjs);
          }(document, 'script', 'facebook-jssdk'));</script>

          <!-- Your share button code -->
          <div class="fb-share-button"
              data-href="%s"
              data-layout="button">
          </div>
        </div>

        <div style="float:right;margin:4px 10px 0px 10px;">

<a style="visibility:hidden;" href="https://twitter.com/share" class="twitter-share-button" data-text="Introducing Volupedia, a Wikipedia mirror powered by @Sketchfab 3D previews" data-dnt="true">Tweet</a>
<script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?'http':'https';if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+'://platform.twitter.com/widgets.js';fjs.parentNode.insertBefore(js,fjs);}}(document, 'script', 'twitter-wjs');</script>

        </div>

      </div>
    </div>
  """ % (json.dumps(random_pages), len(random_pages), request.url)))
  body_elt[0].attrib["style"] = "position:relative;top:28px;"

  # Remove the link ref=canonical which messes up with sharers
  canonical = tree.cssselect("link[rel=canonical]")
  if len(canonical) > 0:
    canonical[0].getparent().remove(canonical[0])

  return lxml.html.tostring(tree)


class InfoboxInserter(object):
  """ Manages insertion in Wikipedia's infoboxes. http://en.volupedia.org/wiki/France """
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
  """ Manages insertion in Wikipedia's image thumbnails. http://en.volupedia.org/wiki/Chair """
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


def replace_domain(url, replace_url, protocol=True):
  urlparts = list(urlparse(url))
  if protocol:
    urlparts[0] = urlparse(replace_url)[0]
  urlparts[1] = urlparse(replace_url)[1]
  return urlunparse(urlparts)


def get_sketchfab_embed(sketchfab_model, width=640, height=480):

  html = '<iframe width="%s" height="%s" src="https://sketchfab.com/models/%s/embed" frameborder="0" allowfullscreen mozallowfullscreen="true" webkitallowfullscreen="true" onmousewheel=""></iframe><div style="text-align:center;">"%s" by <a href="https://sketchfab.com/%s">%s</a></div>' % (
    width, height, sketchfab_model["uid"], sketchfab_model.get("name", "Unknown"), sketchfab_model["user"]["username"], sketchfab_model["user"]["displayName"]
  )

  return html


def search_sketchfab_models(search):
  api_url = "https://sketchfab.com/i/search?count=1&offset=0&q=%s&restricted=0&sort_by=-relevance&type=models" % urllib.quote(search.encode("utf-8"))
  js = json.loads(requests.get(api_url).content)

  for res in js.get("results"):
    yield res


# Run the app!
if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  debug = bool(os.environ.get("DEBUG"))
  app.run(host='0.0.0.0', port=port, debug=debug)
