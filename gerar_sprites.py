import os
from PIL import Image

def processar_sprites():
    input_path = "bonecos.jpg.jpg"
    output_dir = "sprites"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    img = Image.open(input_path).convert("RGB")
    width, height = img.size
    
    rows = 5
    cols = 4
    
    cell_w = width / cols
    cell_h = height / rows
    
    total_arquivos = 0
    
    for r in range(rows):
        row_sprites = []
        row_boxes = []
        
        # Passo 1: Extrair e limpar as 4 células da linha
        for c in range(cols):
            x1 = int(c * cell_w) + 8
            y1 = int(r * cell_h) + 8
            x2 = int((c + 1) * cell_w) - 8
            y2 = int((r + 1) * cell_h) - 8
            
            cell_img = img.crop((x1, y1, x2, y2)).convert("RGBA")
            pixels = cell_img.load()
            w, h = cell_img.size
            
            # Tornar o verde (#00FF00 com tolerância) transparente
            for py in range(h):
                for px in range(w):
                    red, green, blue, alpha = pixels[px, py]
                    # Tolerância para verde de fundo chroma key
                    if green > 120 and green > red + 30 and green > blue + 30:
                        pixels[px, py] = (0, 0, 0, 0)
                        
            # Apagar 1 pixel de borda esverdeada (fringe removal)
            # Analisamos pixels opacos que tocam pixels transparentes e têm tom esverdeado
            transparent_mask = set()
            for py in range(h):
                for px in range(w):
                    if pixels[px, py][3] == 0:
                        transparent_mask.add((px, py))
                        
            fringe_pixels = []
            for py in range(h):
                for px in range(w):
                    if pixels[px, py][3] > 0:
                        # Verifica se é vizinho de algum pixel transparente
                        is_border = False
                        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
                            nx, ny = px + dx, py + dy
                            if (nx, ny) in transparent_mask:
                                is_border = True
                                break
                        if is_border:
                            red, green, blue, alpha = pixels[px, py]
                            if green > red and green > blue:
                                fringe_pixels.append((px, py))
                                
            for px, py in fringe_pixels:
                pixels[px, py] = (0, 0, 0, 0)
                
            # Obter bounding box do conteúdo não transparente
            bbox = cell_img.getbbox()
            if not bbox:
                bbox = (0, 0, w, h)
                
            row_sprites.append(cell_img)
            row_boxes.append(bbox)
            
        # Determinar tamanho unificado e baseline para a linha (mesma pessoa, 4 poses)
        max_w = max(box[2] - box[0] for box in row_boxes)
        max_h = max(box[3] - box[1] for box in row_boxes)
        
        # Adicionar margem/padding uniforme
        padding = 10
        final_w = max_w + padding * 2
        final_h = max_h + padding * 2
        
        # A base (fundo do boneco) deve ficar no mesmo nível vertical relativo
        # Encontramos o ponto mais baixo (y2) de todas as boxes da linha
        max_bottom = max(box[3] for box in row_boxes)
        
        for c in range(cols):
            cell_img = row_sprites[c]
            box = row_boxes[c]
            
            # Cortar o boneco na sua bounding box exata
            cropped = cell_img.crop(box)
            
            # Criar canvas unificado RGBA transparente para a linha
            unified_canvas = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
            
            # Calcular posição de colagem para manter a base (pés) alinhada
            # A base do boneco atual é box[3]. Queremos que todos fiquem alinhados ao mesmo nível base relativo.
            # Alinhamento horizontal centralizado, alinhamento vertical baseado na base inferior.
            sprite_w, sprite_h = cropped.size
            
            paste_x = (final_w - sprite_w) // 2
            # Alinhamento da base: a distância do fundo do canvas até a base do sprite é constante
            # Ou simplesmente alinhar pela base inferior comum:
            baseline_offset = max_bottom - box[3] # ajuste caso haja pequena variação na altura dos pés
            paste_y = final_h - padding - sprite_h - baseline_offset
            
            unified_canvas.paste(cropped, (paste_x, paste_y), cropped)
            
            file_name = f"linha{r+1}_pose{c+1}.png"
            file_path = os.path.join(output_dir, file_name)
            unified_canvas.save(file_path, "PNG")
            
            total_arquivos += 1
            print(f"{file_name} {unified_canvas.width}x{unified_canvas.height}")
            
    print(f"TOTAL: {total_arquivos} arquivos")

if __name__ == "__main__":
    processar_sprites()
