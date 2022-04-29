from game import *
from utils import *
from telegram import User
from urllib.request import urlopen
from PIL import Image
from cairo import Context, SVGSurface, ImageSurface, Surface, Error, FONT_SLANT_NORMAL, FONT_WEIGHT_NORMAL, FORMAT_ARGB32, RadialGradient
import math

'''
TODO

[/] Drawing
    [ ] Change clue's font
    [ ] Differentiate people without photos (by initials?)
    [X] Highlight storyteller better
'''

def draw_card(ctx, card):
    file_jpeg = urlopen(card.url)
    pil_file_jpeg = Image.open(file_jpeg)
    png_filename = f'tmp/card_{card.image_id:0>5}.png'
    pil_file_jpeg.save(png_filename)
    card_surface = ImageSurface.create_from_png(png_filename)

    ctx.scale(1/card_surface.get_width(), 1/card_surface.get_height())
    ctx.set_source_surface(card_surface, 0, 0)
    ctx.paint()
    ctx.scale(card_surface.get_width(), card_surface.get_height())

def draw_profile_pic(ctx,
                     pic_filename,
                     border_color=None,
                     glow_color=None,
                     glow_excess=None,
                     default_filename='assets/default_pic.png'):
    '''Draws profile picture in pic_filename. Just clips a circle around the image.
    If `border_color` is specified, draw a border around the circle of that color.
    If `glow_color` and `glow_excess` are specified, draw a radial gradiant of
    that color around the circle with the end radius 1 + glow_excess, in units
    of the radius of the picture circle.
    If image cannot be found, uses the default_filename'''
    # Assuming pic is a png
    # Ref: https://python-telegram-bot.readthedocs.io/en/stable/telegram.bot.html?highlight=getuserprofile#telegram.Bot.get_user_profile_photos
    # bot.get_user_profile_photos(user_id, ...) --returns--> UserProfilePhotos --.photos[0][0]--> PhotoSize --.get_file()--> File --download(custom_path)--> Baixou o arquivo finalmente
    try:
        pic_surface = ImageSurface.create_from_png(pic_filename)
    except Error:
        pic_surface = ImageSurface.create_from_png(default_filename)

    if glow_color and glow_excess:
        rg = RadialGradient(0.5, 0.5, 0.5, 0.5, 0.5, 0.5*(1 + glow_excess))
        rg.add_color_stop_rgba(0, *glow_color, 1)
        rg.add_color_stop_rgba(1, *glow_color, 0)
        ctx.set_source(rg)
        ctx.arc(0.5, 0.5, 0.5*(1 + glow_excess), 0, math.pi * 2)
        ctx.fill()

    ctx.save()

    ctx.arc(0.5, 0.5, 0.5, 0, 2*math.pi)
    ctx.clip()

    ctx.scale(1/pic_surface.get_width(), 1/pic_surface.get_height())
    ctx.set_source_surface(pic_surface, 0, 0)
    ctx.paint()
    ctx.scale(pic_surface.get_width(), pic_surface.get_height())

    ctx.reset_clip()

    ctx.restore()

    if border_color:
        ctx.arc(0.5, 0.5, 0.5, 0, 2*math.pi)
        ctx.set_source_rgba(*border_color)
        ctx.set_line_width(0.05)
        ctx.stroke()


def draw_background(ctx,
                    clip_width,
                    clip_height,
                    background_filename='assets/paper_background.png'):
    '''Draws a repeating background on a given clipped area'''
    background_surface = ImageSurface.create_from_png(background_filename)

    ctx.scale(1/clip_width, 1/clip_height)
    ctx.rectangle(0, 0, clip_width, clip_height)
    ctx.clip()

    for x in range(1 + clip_width // background_surface.get_width()):
        for y in range(1 + clip_height // background_surface.get_height()):
            ctx.set_source_surface(background_surface,
                                   x*background_surface.get_width(),
                                   y*background_surface.get_height())
            ctx.paint()

    ctx.scale(clip_width, clip_height)

    ctx.reset_clip()

card_hor_border=0.2
score_height=0.15
delta_score_height=0.7*score_height
voted_pic_diam=0.3
voter_pic_diam=0.2
card_aspect_ratio=1.5
results_border=0.1
clue_height=0.2

player_border_color = (0.1, 0.1, 0.1)
storyteller_border_color = (0.9, 0.9, 0)
storyteller_glow_color = (0.9, 0.9, 0)
storyteller_glow_excess = 0.6
score_color = (0.0, 0.0, 0.0)
clue_color = (0.0, 0.0, 0.0)
delta_score_color = (0.0, 0.6, 0.0)

card_width=236/2
def draw_results(ctx, results):
    total_width = (1 + 2*card_hor_border)*len(results.players) + 2*results_border
    total_height = voted_pic_diam + score_height + card_aspect_ratio + voter_pic_diam + clue_height + 2*results_border

    # Draw background
    draw_background(ctx, int(card_width*total_width), int(card_width*total_height))

    ctx.scale(1/total_width,
              1/total_height)
    ctx.select_font_face("Arial",
                         FONT_SLANT_NORMAL,
                         FONT_WEIGHT_NORMAL)
    # Write clue
    ctx.translate(0, total_height - results_border)

    ctx.set_source_rgb(*clue_color)
    ctx.set_font_size(clue_height)
    clue_extents = ctx.text_extents(results.clue)
    ctx.translate(total_width/2 - clue_extents.width / 2 - clue_extents.x_bearing,
                  (clue_extents.height-clue_height)/2)

    ctx.show_text(results.clue)

    ctx.translate(-(total_width/2 - clue_extents.width / 2 - clue_extents.x_bearing),
                  -(clue_extents.height-clue_height)/2)
    ctx.translate(0, -(total_height - results_border))

    ctx.translate(results_border, results_border)
    for player in results.players:
        ctx.translate(card_hor_border, 0)

        # Draw star in storyteller
        if player == results.storyteller:
            border_color = storyteller_border_color
            glow_color = storyteller_glow_color
            glow_excess = storyteller_glow_excess
        else:
            border_color = player_border_color
            glow_color = None
            glow_excess = None

        # Draw profile pic above card
        ctx.translate(1/2 - voted_pic_diam/2, 0)
        ctx.scale(voted_pic_diam, voted_pic_diam)

        draw_profile_pic(ctx, f'tmp/pic_{player.id}.png',
                         border_color,
                         glow_color,
                         glow_excess)

        ctx.scale(1/voted_pic_diam, 1/voted_pic_diam)
        ctx.translate(-(1/2 - voted_pic_diam/2), 0)

        # Draw total and delta scores
        ctx.translate(0, voted_pic_diam + score_height)

        ctx.set_source_rgb(*score_color)
        score_text = str(results.score[player])
        ctx.set_font_size(score_height)
        score_extents = ctx.text_extents(score_text)
        ctx.translate(1/2 - score_extents.width / 2 - score_extents.x_bearing,
                      (score_extents.height-score_height)/2)

        ctx.show_text(score_text)

        ctx.set_source_rgb(*delta_score_color)
        delta_score_text = f'+{results.delta_score[player]}'
        ctx.set_font_size(delta_score_height)
        ctx.show_text(delta_score_text)

        ctx.translate(-(1/2 - score_extents.width / 2 - score_extents.x_bearing),
                      -(score_extents.height-score_height)/2)


        ctx.translate(0, -(voted_pic_diam + score_height))

        # Draw card

        ctx.translate(0, score_height + voted_pic_diam)
        ctx.scale(1, card_aspect_ratio)

        draw_card(ctx, results.table[player])

        ctx.scale(1, 1/card_aspect_ratio)
        ctx.translate(0, - (score_height + voted_pic_diam))

        player_voters = [voter for voter, voted in results.votes.items() if voted == player]
        # Account for when stack of voter pictures would exceed card width
        voter_translation = min(voter_pic_diam, (1-voter_pic_diam)/(len(player_voters)-1)) \
                            if len(player_voters) > 1 else voter_pic_diam
        for voter_n, voter in enumerate(player_voters):
            ctx.translate(voter_n*(voter_translation),
                          voted_pic_diam + score_height + card_aspect_ratio)

            ctx.scale(voter_pic_diam, voter_pic_diam)
            draw_profile_pic(ctx, f'tmp/pic_{voter.id}.png')
            ctx.scale(1/voter_pic_diam, 1/voter_pic_diam)

            ctx.translate(-voter_n*(voter_translation),
                          -(voted_pic_diam + score_height + card_aspect_ratio))

        # Translate to next card
        ctx.translate(1 + card_hor_border, 0)
    ctx.translate(-results_border, -results_border)

def save_results_pic(results, n=0, card_width=236):
    '''Saves results picture in tmp/results_pic_{n}.png. Returns filename'''
    filename = f'tmp/results_pic_{n}.png'
    total_width = (1 + 2*card_hor_border)*len(results.players) + 2*results_border
    total_height = voted_pic_diam + score_height + card_aspect_ratio + voter_pic_diam + clue_height + 2*results_border

    width = int(card_width*total_width)
    height = int(card_width*total_height)

    surface = ImageSurface(FORMAT_ARGB32, width, height)
    ctx = Context(surface)

    ctx.scale(width, height)

    draw_results(ctx, results)

    surface.write_to_png(filename)

    return filename
