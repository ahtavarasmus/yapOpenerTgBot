import os
import re
from playwright.async_api import async_playwright
from telegram import Update,InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()

# Replace this with your own Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_BEARER')

async def start(update: Update, context):
    await update.message.reply_text('Bot is running. Use /preview command followed by a Twitter/X link to get a preview.')

async def get_video_link(url):
    # https://twitsave.com/info?url=<url param here>
    # find a video from the page with playwright and get the video src url
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"https://twitsave.com/info?url={url}")
        await page.wait_for_load_state("networkidle")  # Wait until the network is idle
 
        # Check for videos
        video_elems = await page.query_selector_all("video")
        video_urls = [await video.get_attribute('src') for video in video_elems] if video_elems else []
        if video_urls:
            video_url = video_urls[0]
        else:
            video_url = None
        
        await browser.close()

        return video_url


        

    

async def extract_tweet_info(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(url)
        await page.wait_for_load_state("networkidle")  # Wait until the network is idle
        
        tweet_info = {}

        # Wait for the tweet content to load
        await page.wait_for_selector("article")  # Increased timeout
        
        # Extract author
        username = page.locator('div[data-testid="User-Name"] a span').first
        

        tweet_info['url'] = url
        
        # Extract the text content of the username
        tweet_info['author'] = await username.text_content() if username else 'Unknown'
        
        # Extract date
        date_elem = await page.query_selector("time")
        tweet_info['date'] = await date_elem.get_attribute('datetime') if date_elem else 'Unknown'
        
        # Extract title (tweet text)
        title_elem = await page.query_selector("article div[lang]")
        tweet_info['title'] = await title_elem.inner_text() if title_elem else ''
        
        # Extract tweet text (if different from title)
        text_elem = await page.query_selector("article div[lang]")
        tweet_info['text'] = await text_elem.inner_text() if text_elem else ''
        
        # Check for image
        img_elems = await page.query_selector_all("img[src*='media']")
        tweet_info['media_images'] = [await img.get_attribute('src') for img in img_elems] if img_elems else None

        video_link = get_video_link(url)
        tweet_info['video'] = video_link
        
        await browser.close()
        
        return tweet_info

async def handle_message(update: Update, context):
    message_text = update.message.text
    twitter_links = re.findall(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/\S+', message_text)
    remaining_text = re.sub(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/\S+', '', message_text).strip()
    # Get the user who sent the message
    user = update.message.from_user
    user_name = user.full_name if user.full_name else user.username
    
    if twitter_links:
        if update.message.reply_to_message:
            replied_message = update.message.reply_to_message
            # Get the user who sent the replied-to message
            replied_user_name = replied_message.from_user.full_name if replied_message.from_user.full_name else replied_message.from_user.username

            replied_message_text = replied_message.text
            print("reply",replied_message_text)


        for link in twitter_links:
            try:
                tweet_info = await extract_tweet_info(link)
                
                if tweet_info:

                    response = f"{user_name}: {remaining_text}\n"
                    if update.message.reply_to_message and replied_message_text:
                        response = f"{user_name}'s reply's post: \n\n{tweet_info['author']}\n\n{tweet_info['text']}"
                    else:
                        response += f"\n{tweet_info['author']}\n\n{tweet_info['text']}\n\n{tweet_info['url']}"

                    try:
                        # Delete the user's original message
                        
                        if tweet_info['media_images']:
                            if len(tweet_info['media_images']) == 1:
                                for image_url in tweet_info['media_images']:
                                    print(f"hey image: {image_url}")
                                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url, caption=response)
                                    print("send?")
                            else:
                                media_files = []
                                for image_url in tweet_info['media_images']:
                                    # Create a caption for each image
                                    media_files.append(InputMediaPhoto(media=image_url))

                                # Send the media group
                                await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_files)

                                await context.bot.send_message(
                                    chat_id=update.effective_chat.id,
                                    text=response
                                )
                        else:
                            await context.bot.send_message(
                                    chat_id=update.effective_chat.id,
                                    text=response
                                )
                        if not update.message.reply_to_message:
                            await context.bot.delete_message(
                                chat_id=update.effective_chat.id,
                                message_id=update.message.message_id
                            )


                    except Exception as e:

                        # Log specific error for debugging
                        await update.message.reply_text(f"Error editing message: {str(e)}")
                else:
                    await update.message.reply_text("Couldn't fetch tweet content. The tweet might be private or deleted.")
            except Exception as e:
                # Log specific error for debugging
                await update.message.reply_text(f"Error fetching tweet: {str(e)}")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()

