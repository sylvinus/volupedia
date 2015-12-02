# Volupedia

http://www.volupedia.org

Volupedia is an experiment mixing [Wikipedia](http://www.wikipedia.org) pages with 3D models from [Sketchfab](http://www.sketchfab.com).

It is a reverse proxy of Wikipedia that replaces the main image of the article by a Sketchfab embed, if there is one that matches the title of the article.

Feedback & bugfixes welcome!

# Articles with interesting 3D models

 - http://en.volupedia.org/wiki/Tesla_Motors
 - http://en.volupedia.org/wiki/Rio_de_Janeiro
 - http://en.volupedia.org/wiki/Samsung
 - http://en.volupedia.org/wiki/Solar_Impulse
 - http://en.volupedia.org/wiki/British_Museum
 - http://en.volupedia.org/wiki/Kathmandu
 - http://en.volupedia.org/wiki/Barack_Obama
 - http://en.volupedia.org/wiki/Solar_System
 - http://en.volupedia.org/wiki/NEAR_Shoemaker
 - http://en.volupedia.org/wiki/Stegosaurus
 - http://en.volupedia.org/wiki/Moai
 - http://en.volupedia.org/wiki/Minecraft
 - http://en.volupedia.org/wiki/Yoda
 - http://en.volupedia.org/wiki/Dwayne_Johnson

# TODO

 - blacklist some sketchfab tags (eggs?)
 - insert more than 1 model?
 - better sketchfab order (likes+relevance?)
 - pre-process article titles (remove parentheses?)
 - Non-english wikipedia domains

# How to test locally

```
pip install -r requirements.txt
python server.py
```

Then open http://localhost:5000