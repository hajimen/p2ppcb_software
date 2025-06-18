import sys
import pickle


if __name__ == '__main__':
    from kle_scraper import scrape
    keyboard = scrape(sys.argv[1], sys.argv[2])
    buf = pickle.dumps(keyboard)
    sys.stdout.buffer.write(buf)
    sys.exit(0)
