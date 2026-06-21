import time
import sys
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    print("Could not import rgbmatrix!")
    sys.exit(1)

def test():
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.gpio_slowdown = 4
    options.hardware_mapping = 'regular'
    options.drop_privileges = False
    
    print("Initializing matrix...")
    try:
        matrix = RGBMatrix(options=options)
        canvas = matrix.CreateFrameCanvas()
        
        # Fill canvas with solid red
        print("Filling display with solid red...")
        for x in range(64):
            for y in range(32):
                canvas.SetPixel(x, y, 255, 0, 0)
                
        matrix.SwapOnVSync(canvas)
        print("Display should now be RED. Waiting 5 seconds...")
        time.sleep(5)
        
        matrix.Clear()
        print("Clear successful.")
    except Exception as e:
        print("Failed to initialize or write to matrix:", e)

if __name__ == '__main__':
    test()
