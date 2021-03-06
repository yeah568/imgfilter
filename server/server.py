from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, url

import epilepsy
import gifutils
import json
import os
import nude
import ms_cv
import tag as tagger
import hashlib

class MainHandler(RequestHandler):
  def get(self):
    self.write("Hello, world")

class ImageHandler(RequestHandler):
  def post(self):
    print("request!")
    image_data = self.request.files['image'][0]['body']
    image_name = self.get_argument('name')
    filename, file_extension = os.path.splitext(image_name)
    hash_name = hashlib.md5(filename.encode())
    image_name = hash_name.hexdigest() + ".jpg"
    blocked_words = json.loads(self.get_argument('block'))
    blockNSFW = self.get_argument('blockNSFW')

    # Write the file to disk
    open("temp/%s" % image_name, "wb+").write(image_data)

    # Determine block or not
    block, caption, reason = should_block("temp/%s" % image_name, blocked_words, blockNSFW)

    self.finish(json.dumps({"block": block, "caption": caption, "reason": reason}))

class GIFHandler(RequestHandler):
  def post(self):
    gif_data = self.request.files['gif'][0]['body']
    gif_name = self.get_argument('name')
    filename, file_extension = os.path.splitext(gif_name)
    hash_name = hashlib.md5(filename.encode())
    gif_name = hash_name.hexdigest() + ".gif"
    blocked_words = json.loads(self.get_argument('block'))
    blockEpileptic = self.get_argument('blockEpileptic')
    blockNSFW = self.get_argument('blockNSFW')

    # Write the file to disk
    open("temp/%s" % gif_name, "wb+").write(gif_data)

    # Determine block or not
    block, caption, reason = should_block_gif("temp/%s" % gif_name, blocked_words, blockEpileptic, blockNSFW)

    self.finish(json.dumps({"block": block, "caption": caption, "reason": reason}))

def should_block_gif(gif_path, blocked_words, blockEp, blockNSFW):
  """
  Determine whether or not to block GIF.
  """
  if blockEp:
    res = not epilepsy.is_gif_safe(gif_path)
    image_paths = gifutils.save_gif_frames(gif_path)
    block, caption, reason = should_block(image_paths[0], blocked_words, blockNSFW)
    if res:
      return True, caption, "GIF may trigger epileptic seizures"
  
  if blockNSFW:
    for image in image_paths:
      block, _, reason = should_block(image, blocked_words, blockNSFW)
      if block:
        return True, caption, reason

  return False, caption, "Our deep learning algorithms identified this content as safe"

def should_block(image_path, blocked_words, blockNSFW):
  """
  Determine whether or not to block, and return the caption.
  """
  vgg_tags = [e[0] for e in tagger.predict_tags(image_path)]
  ms_tags = ms_cv.predict_tags(image_path)
  ms_caption = ms_cv.predict_caption(image_path)

  for word in blocked_words:
    for tag in vgg_tags + ms_tags:
      if word in tag:
        return True, ms_caption, "Blacklist object, %s, identified" % word

    if word in ms_caption.lower():
      return True, ms_caption, "Blacklist object, %s, identified" % word

  if blockNSFW:
    if nude.has_nudity(image_path):
      return True, ms_caption, "Content identified as NSFW"

  return False, ms_caption, "Our deep learning algorithms identified this content as safe"

def make_app():
  return Application([
    url(r"/", MainHandler),
    url(r"/test", ImageHandler),
    url(r"/image", ImageHandler),
    url(r"/gif", GIFHandler),
  ])


def main():
  app = make_app()
  app.listen(9999)
  print('Running app.')
  IOLoop.instance().start()

if __name__ == "__main__":
  main()

