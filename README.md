# volupedia

http://www.volupedia.org

Volupedia is an experiment mixing Wikipedia pages with 3D models from Sketchfab.

It is a reverse proxy of Wikipedia that replaces the main image of the article by a Sketchfab embed, if there is one that matches the title of the article.

Feedback & bugfixes welcome!

# Articles with interesting 3D models

 - http://en.volupedia.org/wiki/Eiffel_Tower
 - http://en.volupedia.org/wiki/Solar_System
 - http://en.volupedia.org/wiki/Palmyra

# TODO

 - blacklist some sketchfab tags (eggs?)
 - insert more than 1 model?
 - conflict between top banner and WP fundraising header?
 - better sketchfab order (likes+relevance?)
 - Non-english wikipedia domains

# How to test locally

```
pip install -r requirements.txt
python server.py
```

Then open http://localhost:5000