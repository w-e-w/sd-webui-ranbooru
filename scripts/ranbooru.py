from io import BytesIO
import random
import requests
import modules.scripts as scripts
import gradio as gr
import os
from PIL import Image
import numpy as np
import importlib

from modules import images
from modules.processing import process_images, StableDiffusionProcessingImg2Img
from modules import shared
from modules.img2img import img2img
from modules.sd_hijack import model_hijack
from modules.deepbooru import DeepDanbooru

extensions_root = scripts.basedir()
user_dir = os.path.join(extensions_root, 'user')
user_remove_dir = os.path.join(user_dir, 'remove')
user_search_dir = os.path.join(user_dir, 'search')
os.makedirs(user_dir, exist_ok=True)
os.makedirs(user_remove_dir, exist_ok=True)
os.makedirs(user_search_dir, exist_ok=True)

COLORED_BG = ['black_background','aqua_background','white_background','colored_background','gray_background','blue_background','green_background','red_background','brown_background','purple_background','yellow_background','orange_background','pink_background','plain','transparent_background','simple_background','two-tone_background','grey_background']
ADD_BG = ['outdoors','indoors']
BW_BG = ['monochrome','greyscale','grayscale']
POST_AMOUNT = 100
DEBUG = False
RATING_TYPES = {
    "none": {
        "All": "All"
    },
    "full": {
        "All": "All",
        "Safe": "safe",
        "Questionable": "questionable",
        "Explicit": "explicit"
    },
    "single": {
        "All": "All",
        "Safe": "g",
        "Sensitive": "s",
        "Questionable": "q",
        "Explicit": "e"
    }
}
RATINGS = {
    "e621": RATING_TYPES['full'],
    "danbooru": RATING_TYPES['single'],
    "aibooru": RATING_TYPES['full'],
    "yande.re": RATING_TYPES['full'],
    "konachan": RATING_TYPES['full'],
    "safebooru": RATING_TYPES['none'],
    "rule34": RATING_TYPES['full'],
    "xbooru": RATING_TYPES['full'],
    "gelbooru": RATING_TYPES['single']
}

def get_available_ratings(booru):
    mature_ratings =  gr.Radio.update(choices=RATINGS[booru].keys(), value="All")
    return mature_ratings

def show_fringe_benefits(booru):
    if booru == 'gelbooru':
        return gr.Checkbox.update(visible=True)
    else:
        return gr.Checkbox.update(visible=False)

def check_exception(booru, parameters):
    post_id = parameters.get('post_id')
    tags = parameters.get('tags')
    if booru == 'konachan' and post_id:
        raise Exception("Konachan does not support post IDs")
    if booru == 'yande.re' and post_id:
        raise Exception("Yande.re does not support post IDs")
    if booru == 'e621' and post_id:
        raise Exception("e621 does not support post IDs")
    if booru == 'danbooru' and len(tags.split(',')) > 1:
        raise Exception("Danbooru does not support multiple tags. You can have only one tag.")

class Booru():
    
    def __init__(self, booru, booru_url):
        self.booru = booru
        self.booru_url = booru_url
        self.headers = {'user-agent': 'my-app/0.0.1'}
        
    def get_data(self,add_tags,max_pages=10, id=''):
        pass
    
    def get_post(self,add_tags,max_pages=10, id=''):
        pass
    
class Gelbooru(Booru):
    
    def __init__(self, fringe_benefits):
        super().__init__('gelbooru', f'https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        self.fringeBenefits = fringe_benefits

    def get_data(self, add_tags, max_pages=10, id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        if self.fringeBenefits:
            res = requests.get(self.booru_url, cookies={'fringeBenefits': 'yup'})
        else:
            res = requests.get(self.booru_url)
        data = res.json()
        return data
    
    def get_post(self, add_tags, max_pages=10, id=''):
        return self.get_data(add_tags, max_pages, "&id="+id)
    
    
class XBooru(Booru):
    
    def __init__(self):
        super().__init__('xbooru', f'https://xbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10, id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        for post in data:
            post['file_url'] = f"https://xbooru.com/images/{post['directory']}/{post['image']}"
        return {'post': data}
    
    def get_post(self, add_tags, max_pages=10, id=''):
        return self.get_data(add_tags, max_pages, "&id="+id)
    
class Rule34(Booru):
    
    def __init__(self):
        super().__init__('rule34', f'https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        return {'post': data}
    
    def get_post(self, add_tags, max_pages=10, id=''):
        return self.get_data(add_tags, max_pages, "&id="+id)
    
class Safebooru(Booru):
    
    def __init__(self):
        super().__init__('safebooru', f'https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        for post in data:
            post['file_url'] = f"https://safebooru.org/images/{post['directory']}/{post['image']}"
        return {'post': data}
    
    def get_post(self, add_tags, max_pages=10, id=''):
        return self.get_data(add_tags, max_pages, "&id="+id)
    
class Konachan(Booru):
    
    def __init__(self):
        super().__init__('konachan', f'https://konachan.com/post.json?limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        return {'post': data}
    
    def get_post(self, add_tags, max_pages=10, id=''):
        raise Exception("Konachan does not support post IDs")
    
class Yandere(Booru):
    
    def __init__(self):
        super().__init__('yande.re', f'https://yande.re/post.json?limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        return {'post': data}
    
    def get_post(self, add_tags, max_pages=10, id=''):
        raise Exception("Yande.re does not support post IDs")
    
class AIBooru(Booru):
    
    def __init__(self):
        super().__init__('AIBooru', f'https://aibooru.online/posts.json?limit={POST_AMOUNT}')
                
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        for post in data:
            post['tags'] = post['tag_string']
        return {'post': data}
    
    def get_post(self, add_tags, max_pages=10, id=''):
        raise Exception("AIBooru does not support post IDs")
    
class Danbooru(Booru):
    
    def __init__(self):
        super().__init__('danbooru', f'https://danbooru.donmai.us/posts.json?limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10, id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url, headers=self.headers)
        data = res.json()
        for post in data:
            post['tags'] = post['tag_string']
        return {'post': data}
    
    def get_post(self, add_tags, max_pages=10, id=''):
        self.booru_url = f"https://danbooru.donmai.us/posts/{id}.json"
        res = requests.get(self.booru_url, headers=self.headers)
        data = res.json()
        data['tags'] = data['tag_string']
        data = {'post': [data]}
        return data
    
class e621(Booru):
    
    def __init__(self):
        super().__init__('danbooru', f'https://e621.net/posts.json?limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10, id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url, headers=self.headers)
        data = res.json()['posts']
        for post in data:
            temp_tags = []
            sublevels = ['general','artist','copyright','character','species']
            for sublevel in sublevels:
                temp_tags.extend(post['tags'][sublevel])
            post['tags'] = ' '.join(temp_tags)
            post['score'] = post['score']['total']
        return {'post': data}
    
    def get_post(self, add_tags, max_pages=10, id=''):
        self.get_data(add_tags, max_pages, "&id="+id)
    
def generate_chaos(pos_tags,neg_tags,chaos_amount):
    # create a list with the tags in the prompt and in the negative prompt
    chaos_list = [tag for tag in pos_tags.split(',') + neg_tags.split(',') if tag.strip() != '']
    # distinct the list
    chaos_list = list(set(chaos_list))
    random.shuffle(chaos_list)
    # put 50% of the tags in the prompt and the remaining 50% in the negative prompt
    len_list = round(len(chaos_list)*chaos_amount)
    pos_list = chaos_list[len_list:]
    pos_prompt = ','.join(pos_list)
    neg_list = chaos_list[:len_list]
    random.shuffle(neg_list)
    neg_prompt = ','.join(neg_list)
    return pos_prompt, neg_prompt

def resize_image(img, width, height, cropping=True):
    """Resize image to specified width and height"""
    if cropping:
        # resize the picture and center crop it
        # example: you have a 100x200 picture and width=300 and height=300
        # resize to 300x600 and crop to 300x300 from the center
        x,y = img.size
        if x < y:
            # scale to width keeping aspect ratio
            wpercent = (width / float(img.size[0]))
            hsize = int((float(img.size[1]) * float(wpercent)))
            img_new = img.resize((width, hsize))
            if img_new.size[1] < height:
                # scale to height keeping aspect ratio
                hpercent = (height / float(img.size[1]))
                wsize = int((float(img.size[0]) * float(hpercent)))
                img_new = img.resize((wsize, height))
        else:
            ypercent = (height / float(img.size[1]))
            wsize = int((float(img.size[0]) * float(ypercent)))
            img_new = img.resize((wsize, height))
            if img_new.size[0] < width:
                xpercent = (width / float(img.size[0]))
                hsize = int((float(img.size[1]) * float(xpercent)))
                img_new = img.resize((width, hsize))
            
        # crop center
        x,y = img_new.size
        left = (x - width)/2
        top = (y - height)/2
        right = (x + width)/2
        bottom = (y + height)/2
        img = img_new.crop((left, top, right, bottom))
    else:
        img = img.resize((width, height))
    return img

class Script(scripts.Script):   
    
    def __init__(self):
        self.previous_loras = ''
        self.last_img = []
        self.real_steps = 0
        self.version = "1.2"
        self.initialize_folders()
        self.ddb = DeepDanbooru()
        self.original_prompt = ''
        
    def initialize_folders(self):
        # create two files: tags_search and tags_remove if they don't exist
        if not os.path.exists(f'{user_search_dir}/tags_search.txt'):
            with open(f'{user_search_dir}/tags_search.txt', 'w') as f:
                f.write('')
        if not os.path.exists(f'{user_remove_dir}/tags_remove.txt'):
            with open(f'{user_remove_dir}/tags_remove.txt', 'w') as f:
                f.write('')
                
    def get_files(self, path):
        files = []
        for file in os.listdir(path):
            if file.endswith('.txt'):
                files.append(file)
        return files
        
    def hide_object(self, obj, booru):
        print(f'hide_object: {obj}, {booru.value}')
        if booru.value == 'konachan' or booru.value == 'yande.re':
            obj.interactive = False
        else:
            obj.interactive = True

    def title(self):

        return "Ranbooru"

    def show(self, is_img2img):

        return scripts.AlwaysVisible
    
    def ui(self, is_img2img):
        with gr.Group():
            with gr.Accordion("Ranbooru", open = False):
                enabled = gr.Checkbox(label="Enable")
                booru = gr.Dropdown(["gelbooru","rule34","safebooru","danbooru","konachan",'yande.re','aibooru','xbooru','e621'], label="Booru", value="gelbooru")
                max_pages = gr.Slider(label="Max Pages", minimum=1, maximum=100,value=100, step=1)
                gr.Markdown("""## Post""")
                post_id = gr.Textbox(lines=1, label="Post ID")
                gr.Markdown("""## Tags""")
                tags = gr.Textbox(lines=1, label="Tags to Search (Pre)")
                remove_tags = gr.Textbox(lines=1, label="Tags to Remove (Post)")
                mature_rating = gr.Radio(RATINGS['gelbooru'].keys(), label="Mature Rating", value="All")
                remove_bad_tags = gr.Checkbox(label="Remove bad tags", value=True)
                shuffle_tags = gr.Checkbox(label="Shuffle tags", value=True)
                change_dash = gr.Checkbox(label='Convert "_" to spaces', value=False)
                same_prompt = gr.Checkbox(label="Use same prompt for all images", value=False)
                fringe_benefits = gr.Checkbox(label="Fringe Benefits", value=True)
                limit_tags = gr.Slider(value=1.0, label="Limit tags", minimum=0.05, maximum=1.0, step=0.05)
                max_tags = gr.Slider(value=100, label="Max tags", minimum=1, maximum=100, step=1)
                change_background = gr.Radio(["Don't Change","Add Background","Remove Background","Remove All"], label="Change Background", value="Don't Change")
                change_color = gr.Radio(["Don't Change","Colored","Limited Palette","Monochrome"], label="Change Color", value="Don't Change")
                sorting_order = gr.Radio(["Random","High Score","Low Score"], label="Sorting Order", value="Random")
                
                booru.change(get_available_ratings, booru, mature_rating) # update available ratings
                booru.change(show_fringe_benefits, booru, fringe_benefits) # display fringe benefits checkbox if gelbooru is selected
                
                gr.Markdown("""\n---\n""")
                with gr.Group():
                    with gr.Accordion("Img2Img", open = False):
                        use_img2img = gr.Checkbox(label="Use img2img", value=False)
                        use_ip = gr.Checkbox(label="Send to Controlnet", value=False)
                        denoising = gr.Slider(value=0.75, label="Denoising", minimum=0.05, maximum=1.0, step=0.05)
                        use_last_img = gr.Checkbox(label="Use last image as img2img", value=False)
                        crop_center = gr.Checkbox(label="Crop Center", value=False)
                        use_deepbooru = gr.Checkbox(label="Use Deepbooru", value=False)
                with gr.Group():
                    with gr.Accordion("File", open = False):
                        use_search_txt = gr.Checkbox(label="Use tags_search.txt", value=False)
                        choose_search_txt = gr.Dropdown(self.get_files(user_search_dir), label="Choose tags_search.txt", value="")
                        use_remove_txt = gr.Checkbox(label="Use tags_remove.txt", value=False)
                        choose_remove_txt = gr.Dropdown(self.get_files(user_remove_dir), label="Choose tags_remove.txt", value="")
                with gr.Group():
                    with gr.Accordion("Extra", open = False):
                        with gr.Box():
                            mix_prompt = gr.Checkbox(label="Mix prompts", value=False)
                            mix_amount = gr.Slider(value=2, label="Mix amount", minimum=2, maximum=10, step=1)
                        with gr.Box():
                            chaos_mode = gr.Radio(["None","Chaos","Less Chaos"], label="Chaos Mode", value="None")
                            chaos_amount = gr.Slider(value=0.5, label="Chaos Amount %", minimum=0.1, maximum=1, step=0.05)
                        with gr.Box():
                            negative_mode = gr.Radio(["None","Negative"], label="Negative Mode", value="None")
                            use_same_seed = gr.Checkbox(label="Use same seed for all pictures", value=False)
        with gr.Group():
            with gr.Accordion("LoRAnado", open = False):
                with gr.Box():
                    lora_enabled = gr.Checkbox(label="Use LoRAnado", value=False)
                    lora_lock_prev = gr.Checkbox(label="Lock previous LoRAs", value=False)
                    lora_folder = gr.Textbox(lines=1, label="LoRAs Subfolder")
                    lora_amount = gr.Slider(default=1, label="LoRAs Amount", minimum=1, maximum=10, step=1)
                with gr.Box():
                    lora_min = gr.Slider(value=-1.0, label="Min LoRAs Weight", minimum=-1.0, maximum=1, step=0.1)
                    lora_max = gr.Slider(value=1.0, label="Max LoRAs Weight", minimum=-1.0, maximum=1.0, step=0.1)
                    lora_custom_weights = gr.Textbox(lines=1, label="LoRAs Custom Weights")
        return [enabled,tags,booru,remove_bad_tags,max_pages,change_dash,same_prompt,fringe_benefits,remove_tags,use_img2img,denoising,use_last_img,change_background,change_color,shuffle_tags,post_id,mix_prompt,mix_amount,chaos_mode,negative_mode,chaos_amount,limit_tags,max_tags,sorting_order,mature_rating,lora_folder,lora_amount,lora_min,lora_max,lora_enabled,lora_custom_weights,lora_lock_prev,use_ip,use_search_txt,use_remove_txt,choose_search_txt,choose_remove_txt,crop_center, use_deepbooru, use_same_seed]
                    
    def check_orientation(self, img):
        """Check if image is portrait, landscape or square"""
        x,y = img.size
        if x/y > 1.2:
            return [768,512]
        elif y/x > 1.2:
            return [512,768]
        else:
            return [768,768]
        
    def loranado(self,lora_enabled,lora_folder,lora_amount,lora_min,lora_max,lora_custom_weights,p,lora_lock_prev):
        lora_prompt = ''
        if lora_enabled:
            if lora_lock_prev:
                lora_prompt = self.previous_loras
            else:
                loras = []
                loras = os.listdir(f'{lora_folder}')
                # get only .safetensors files
                loras = [lora.replace('.safetensors','') for lora in loras if lora.endswith('.safetensors')]                
                for l in range(0, lora_amount):
                    lora_weight = 0
                    if lora_custom_weights != '':
                        lora_weight = float(lora_custom_weights.split(',')[l])
                    while lora_weight == 0:
                        lora_weight = round(random.uniform(lora_min, lora_max), 1)
                    lora_prompt += f'<lora:{random.choice(loras)}:{lora_weight}>'
                    self.previous_loras = lora_prompt
        if lora_prompt:
            if type(p.prompt) == list:
                for num, pr in enumerate(p.prompt):
                    p.prompt[num] = f'{lora_prompt} {pr}'
            else:
                p.prompt = f'{lora_prompt} {p.prompt}'
        return p

    def before_process(self, p, enabled, tags, booru, remove_bad_tags,max_pages,change_dash,same_prompt,fringe_benefits,remove_tags,use_img2img,denoising,use_last_img,change_background,change_color,shuffle_tags,post_id,mix_prompt,mix_amount,chaos_mode,negative_mode,chaos_amount,limit_tags,max_tags,sorting_order,mature_rating,lora_folder,lora_amount,lora_min,lora_max,lora_enabled,lora_custom_weights,lora_lock_prev,use_ip,use_search_txt,use_remove_txt,choose_search_txt,choose_remove_txt,crop_center,use_deepbooru,use_same_seed):
        if enabled:
            # Initialize APIs
            booru_apis = {
                'gelbooru': Gelbooru(fringe_benefits),
                'rule34': Rule34(),
                'safebooru': Safebooru(),
                'danbooru': Danbooru(),
                'konachan': Konachan(),
                'yande.re': Yandere(),
                'aibooru': AIBooru(),
                'xbooru': XBooru(),
                'e621': e621(),
            }
            self.original_prompt = p.prompt
            # Check if compatible
            check_exception(booru, {'tags':tags,'post_id':post_id})

            # Manage Bad Tags
            bad_tags = []
            if remove_bad_tags:
                bad_tags = ['mixed-language_text','watermark','text','english_text','speech_bubble','signature','artist_name','censored','bar_censor','translation','twitter_username',"twitter_logo",'patreon_username','commentary_request','tagme','commentary','character_name','mosaic_censoring','instagram_username','text_focus','english_commentary','comic','translation_request','fake_text','translated','paid_reward_available','thought_bubble','multiple_views','silent_comic','out-of-frame_censoring','symbol-only_commentary','3koma','2koma','character_watermark','spoken_question_mark','japanese_text','spanish_text','language_text','fanbox_username','commission','original','ai_generated','stable_diffusion','tagme_(artist)','text_bubble','qr_code','chinese_commentary','korean_text','partial_commentary','chinese_text','copyright_request','heart_censor','censored_nipples','page_number','scan','fake_magazine_cover','korean_commentary']
            if ',' in remove_tags:
                bad_tags.extend(remove_tags.split(','))
            else:
                bad_tags.append(remove_tags)
            if use_remove_txt:
                bad_tags.extend(open(f'scripts/ranbooru/remove/{choose_remove_txt}', 'r').read().split(','))
                
            # Manage Backgrounds
            if change_background == 'Add Background':
                bad_tags.extend(COLORED_BG)
                p.prompt = (p.prompt + ',' if p.prompt else '') + f'detailed_background,{random.choice(["outdoors","indoors"])}'
            elif change_background == 'Remove Background':
                bad_tags.extend(ADD_BG)
                p.prompt = (p.prompt + ',' if p.prompt else '') + 'plain_background,simple_background,' + random.choice(COLORED_BG)
            elif change_background == 'Remove All':
                bad_tags.extend(COLORED_BG)
                bad_tags.extend(ADD_BG)
            if change_color == 'Colored':
                bad_tags.extend(BW_BG)
            elif change_color == 'Limited Palette':
                p.prompt = (p.prompt + ',' if p.prompt else '') + '(limited_palette:1.3)'
            elif change_color == 'Monochrome':
                p.prompt = (p.prompt + ',' if p.prompt else '') + ','.join(BW_BG)
            
            add_tags = ''
            if use_search_txt:
                if tags:
                    tags += ','+open(f'scripts/ranbooru/search/{choose_search_txt}', 'r').read()
                else:
                    tags = open(f'scripts/ranbooru/search/{choose_search_txt}', 'r').read()
            if tags != '':
                add_tags = f'&tags=-animated+{tags.replace(",", "+")}'
                if mature_rating != 'All':
                    add_tags += f'+rating:{RATINGS[booru][mature_rating]}'
            else:
                add_tags = '&tags=-animated'
            
            # Getting Data
            api_url = ''
            random_post = {'preview_url':''}
            prompts = []
            last_img = []
            data = {'post': [{'tags': ''}]}
            preview_urls = []
            api_url = booru_apis.get(booru, Gelbooru(fringe_benefits))
            print(f'Using {booru}')

            # Manage Post ID
            if post_id:
                data = api_url.get_post(add_tags, max_pages, post_id)
            else:
                data = api_url.get_data(add_tags, max_pages)

            print(api_url.booru_url)
            # Replace null scores with 0
            for post in data['post']:
                if post['score'] == None:
                    post['score'] = 0
            # Sort based on sorting_order
            if sorting_order == 'High Score':
                data['post'] = sorted(data['post'], key=lambda k: k.get('score', 0), reverse=True)
            elif sorting_order == 'Low Score':
                data['post'] = sorted(data['post'], key=lambda k: k.get('score', 0))
            random_numbers = self.random_number(sorting_order, p.batch_size*p.n_iter)
            if post_id:
                print(f'Using post ID: {post_id}')
                random_numbers = [0 for _ in range(0, p.batch_size*p.n_iter)]
            for random_number in random_numbers:
                if same_prompt:
                    random_post = data['post'][random_numbers[0]]
                else:
                    if mix_prompt:
                        temp_tags = []
                        max_tags = 0
                        for _ in range(0, mix_amount):
                            if not post_id:
                                random_mix_number = self.random_number(sorting_order,1)[0]
                            temp_tags.extend(data['post'][random_mix_number]['tags'].split(' '))
                            max_tags = max(max_tags, len(data['post'][random_mix_number]['tags'].split(' ')))
                        # distinct temp_tags
                        temp_tags = list(set(temp_tags))
                        random_post = data['post'][random_number]
                        if len(temp_tags) < max_tags:
                            max_tags = max(len(temp_tags), 20)
                        random_post['tags'] = ' '.join(random.sample(temp_tags, max_tags))
                    else:
                        try:
                            random_post = data['post'][random_number]
                        except IndexError:
                            raise Exception("No posts found with those tags. Try lowering the pages or changing the tags.")
                clean_tags = random_post['tags'].replace('(','\(').replace(')','\)')
                temp_tags = clean_tags.split(' ')
                if shuffle_tags:
                    temp_tags = random.sample(temp_tags, len(temp_tags))
                prompts.append(','.join(temp_tags))
                try:
                    preview_urls.append(random_post['file_url'])
                except KeyError:
                    print('No file_url found, using random pic')
                    preview_urls.append('https://pic.re/image')
                # Debug picture
                if DEBUG:
                    print(random_post)
            if use_img2img or use_deepbooru:
                if use_last_img:
                    response = requests.get(random_post['file_url'], headers=api_url.headers)
                    last_img = [Image.open(BytesIO(response.content))]
                else:
                    for img in preview_urls:
                        response = requests.get(img, headers=api_url.headers)
                        last_img.append(Image.open(BytesIO(response.content)))
            new_prompts = []
            for prompt in prompts:
                new_prompt = ','.join([tag for tag in prompt.split(',') if tag.strip() not in bad_tags])
                # loop over bad_tags containing * and remove from new_prompt every tag that contains the string
                for bad_tag in bad_tags:
                    if '*' in bad_tag:
                        new_prompt = ','.join([tag for tag in new_prompt.split(',') if bad_tag.replace('*','') not in tag])     
                if change_dash:
                    new_prompt = new_prompt.replace("_", " ")
                new_prompts.append(new_prompt)
            prompts = new_prompts
            if len(prompts) == 1:
                print('Processing Single Prompt')
                if p.prompt == '':
                    p.prompt = prompts[-1]
                else:
                    p.prompt = f"{p.prompt},{prompts[-1]}"
                if chaos_mode == 'Chaos':
                    p.prompt, p.negative_prompt = generate_chaos(p.prompt,p.negative_prompt,chaos_amount)
                elif chaos_mode == 'Less Chaos':
                    p.prompt, negative_prompt = generate_chaos(p.prompt,'',chaos_amount)
                    p.negative_prompt = p.negative_prompt+','+negative_prompt
            else:
                print('Processing Multiple Prompts')
                negative_prompts = []
                new_prompts = []
                if chaos_mode == 'Chaos':
                    for prompt in prompts:
                        tmp_prompt, negative_prompt = generate_chaos(prompt,p.negative_prompt,chaos_amount)
                        new_prompts.append(tmp_prompt)
                        negative_prompts.append(negative_prompt)
                    prompts = new_prompts
                    p.negative_prompt = negative_prompts
                elif chaos_mode == 'Less Chaos':
                    for prompt in prompts:
                        tmp_prompt, negative_prompt = generate_chaos(prompt,'',chaos_amount)
                        new_prompts.append(tmp_prompt)
                        negative_prompts.append(negative_prompt)
                    prompts = new_prompts
                    p.negative_prompt = [p.negative_prompt+','+negative_prompt for negative_prompt in negative_prompts]
                else:
                    p.negative_prompt = [p.negative_prompt for _ in range(0, p.batch_size*p.n_iter)]
                if p.prompt == '':
                    p.prompt = prompts
                else:
                    p.prompt = [f"{p.prompt},{prompt}" for prompt in prompts]
                if use_img2img:
                    if len(last_img) < p.batch_size*p.n_iter:
                        last_img = [last_img[0] for _ in range(0, p.batch_size*p.n_iter)]
            if negative_mode == 'Negative':
                #remove tags from p.prompt using tags from the original prompt
                orig_list = self.original_prompt.split(',')
                if type(p.prompt) == list:
                    new_positive_prompts = []
                    new_negative_prompts = []
                    for pr, npp in zip(p.prompt, p.negative_prompt):
                        clean_prompt = pr.split(',')
                        clean_prompt = [tag for tag in clean_prompt if tag not in orig_list]
                        clean_prompt = ','.join(clean_prompt)
                        new_positive_prompts.append(self.original_prompt)
                        new_negative_prompts.append(f'{npp},{clean_prompt}')
                    p.prompt = new_positive_prompts
                    p.negative_prompt = new_negative_prompts
                else:
                    clean_prompt = p.prompt.split(',')
                    clean_prompt = [tag for tag in clean_prompt if tag not in orig_list]
                    clean_prompt = ','.join(clean_prompt)
                    p.negative_prompt = f'{p.negative_prompt},{clean_prompt}'
                    p.prompt = self.original_prompt
            if negative_mode == 'Negative' or chaos_mode in ['Chaos', 'Less Chaos']:
                # NEGATIVE PROMPT FIX
                neg_prompt_tokens = []
                for pr in p.negative_prompt:
                    neg_prompt_tokens.append(model_hijack.get_prompt_lengths(pr)[1])
                if len(set(neg_prompt_tokens)) != 1:
                    print('Padding negative prompts')
                    max_tokens = max(neg_prompt_tokens)
                    for num,neg in enumerate(neg_prompt_tokens):
                        while neg < max_tokens:
                            p.negative_prompt[num] += random.choice(p.negative_prompt[num].split(','))
                            # p.negative_prompt[num] += '_'
                            neg = model_hijack.get_prompt_lengths(p.negative_prompt[num])[1]
            if limit_tags < 1:
                # remove tags from p.prompt in percentage based on limit_tags
                if type(p.prompt) == list:
                    for num, pr in enumerate(p.prompt):
                        clean_prompt = pr.split(',')
                        clean_prompt = clean_prompt[:int(len(clean_prompt)*limit_tags)]
                        clean_prompt = ','.join(clean_prompt)
                        p.prompt[num] = clean_prompt
                else:
                    clean_prompt = p.prompt.split(',')
                    clean_prompt = clean_prompt[:int(len(clean_prompt)*limit_tags)]
                    clean_prompt = ','.join(clean_prompt)
                    p.prompt = clean_prompt
            if max_tags > 0:
                if type(p.prompt) == list:
                    for num, pr in enumerate(p.prompt):
                        clean_prompt = pr.split(',')
                        clean_prompt = clean_prompt[:max_tags]
                        clean_prompt = ','.join(clean_prompt)
                        p.prompt[num] = clean_prompt
                else:
                    clean_prompt = p.prompt.split(',')
                    clean_prompt = clean_prompt[:max_tags]
                    clean_prompt = ','.join(clean_prompt)
                    p.prompt = clean_prompt
                    
            if use_same_seed:
                if p.seed == -1:
                    p.seed = random.randint(0, 2**32-1)
                p.seed = [p.seed for _ in range(0, p.batch_size)]
                    
            # LORANADO
            p = self.loranado(lora_enabled,lora_folder,lora_amount,lora_min,lora_max,lora_custom_weights,p,lora_lock_prev)
            if use_deepbooru and not use_img2img:
                self.last_img = last_img
                p.prompt = self.use_autotagger('deepbooru')
                    
            if use_img2img:
                if not use_ip:
                    self.real_steps = p.steps
                    p.steps = 1
                    self.last_img = last_img
                if use_ip:
                    controlNetModule = importlib.import_module('extensions.sd-webui-controlnet.scripts.external_code',
                                                                'external_code')
                    controlNetList = controlNetModule.get_all_units_in_processing(p)
                    copied_network = controlNetList[0].__dict__.copy()
                    copied_network['enabled'] = True
                    copied_network['weight'] = denoising
                    array_img = np.array(last_img[0])
                    copied_network['image']['image'] = array_img
                    copied_networks = [copied_network] + controlNetList[1:]
                    controlNetModule.update_cn_script_in_processing(p, copied_networks)
                
            else:
                pass
        elif lora_enabled:
            p = self.loranado(lora_enabled,lora_folder,lora_amount,lora_min,lora_max,lora_custom_weights,p,lora_lock_prev)
        else:
            pass
        
    def postprocess(self, p, processed, enabled, tags, booru, remove_bad_tags,max_pages,change_dash,same_prompt,fringe_benefits,remove_tags,use_img2img,denoising,use_last_img,change_background,change_color,shuffle_tags,post_id,mix_prompt,mix_amount,chaos_mode,negative_mode,chaos_amount,limit_tags,max_tags,sorting_order,mature_rating,lora_folder,lora_amount,lora_min,lora_max,lora_enabled,lora_custom_weights,lora_lock_prev,use_ip,use_search_txt,use_remove_txt,choose_search_txt,choose_remove_txt,crop_center,use_deepbooru,use_same_seed):
        if use_img2img and not use_ip and enabled:
            print('Using pictures')
            if crop_center:
                width, height = p.width, p.height
                self.last_img = [resize_image(img, width, height, cropping=True) for img in self.last_img]
            else:
                width, height = self.check_orientation(self.last_img[0])
            final_prompts = p.prompt
            if use_deepbooru:
                final_prompts = self.use_autotagger('deepbooru')
            p = StableDiffusionProcessingImg2Img(
                sd_model=shared.sd_model,
                outpath_samples=shared.opts.outdir_samples or shared.opts.outdir_img2img_samples,
                outpath_grids=shared.opts.outdir_grids or shared.opts.outdir_img2img_grids,
                prompt=final_prompts,
                negative_prompt=p.negative_prompt,
                seed=p.seed,
                sampler_name='Euler a',
                batch_size=p.batch_size,
                n_iter=p.n_iter,
                steps=self.real_steps,
                cfg_scale=p.cfg_scale,
                width=width,
                height=height,
                init_images=self.last_img,
                denoising_strength=denoising,
            )
            proc = process_images(p)
            processed.images = proc.images
            processed.infotexts = proc.infotexts
            if use_last_img:
                    processed.images.append(self.last_img[0])
            else:
                for num,img in enumerate(self.last_img):
                    processed.images.append(img)
                    processed.infotexts.append(proc.infotexts[num+1])
        

    def random_number(self, sorting_order, size):
        # create weights so that the first element is more likely to be chosen than the next one
        weights = np.arange(POST_AMOUNT, 0, -1)
        weights = weights / weights.sum()
        if sorting_order in ('High Score', 'Low Score'):
            random_numbers = np.random.choice(np.arange(POST_AMOUNT), size=size, p=weights, replace=False)
        else:
            random_numbers = random.sample(range(POST_AMOUNT), size)
        return random_numbers 

    def use_autotagger(self,model):
        if model == 'deepbooru':
            orig_prompt = []
            if type(self.original_prompt) == str:
                orig_prompt = [self.original_prompt]
            else:
                orig_prompt = self.original_prompt
            for img,prompt in zip(self.last_img,orig_prompt):
                final_prompts = [prompt+','+self.ddb.tag(img) for img in self.last_img]
            return final_prompts