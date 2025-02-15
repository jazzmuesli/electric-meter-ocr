import os

import cv2
import numpy as np

from utils import *
from processing import *

def non_max_suppression(boxes, probs, overlap_threshold=0.3):
        if len(boxes) == 0:
            return []

        boxes = np.array(boxes, dtype="float")
        probs = np.array(probs)
     
        pick = []
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = x1 + boxes[:, 2]
        y2 = y1 + boxes[:, 3]
     
        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        idxs = np.argsort(probs)
        # keep looping while some indexes still remain in the indexes list
        while len(idxs) > 0:
            # grab the last index in the indexes list and add the index value to the list of
            # picked indexes
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)
    
            # find the largest (x, y) coordinates for the start of the bounding box and the
            # smallest (x, y) coordinates for the end of the bounding box
            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])
    
            # compute the width and height of the bounding box
            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)
    
            # compute the ratio of overlap
            overlap = (w * h) / area[idxs[:last]]
    
            # delete all indexes from the index list that have overlap greater than the
            # provided overlap threshold
            idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlap_threshold)[0])))
            
        # return only the bounding boxes that were picked
        return pick
    
def merge_boxes(boxes, probs, iou_threshold=0.2):
    if len(boxes) <= 5:
        return boxes, probs

    boxes = np.array(boxes, dtype="float")
    probs = np.array(probs)
    
    keep_going = True
    while keep_going:
        new_boxes = []
        new_probs = []
        
        keep_going = False
        
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = x1 + boxes[:, 2]
        y2 = y1 + boxes[:, 3]
     
        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        idxs = np.argsort(probs)
        # keep looping while some indexes still remain in the indexes list
        while len(idxs) > 0:
            highest_prob_idx = idxs[-1]

            # find the largest (x, y) coordinates for the start of the bounding box and the
            # smallest (x, y) coordinates for the end of the bounding box
            xx1 = np.maximum(x1[highest_prob_idx], x1[idxs])
            yy1 = np.maximum(y1[highest_prob_idx], y1[idxs])
            xx2 = np.minimum(x2[highest_prob_idx], x2[idxs])
            yy2 = np.minimum(y2[highest_prob_idx], y2[idxs])

            # compute the width and height of the bounding box
            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)

            # compute the ratio of iou
            iou = (w * h) / (area[idxs] + area[highest_prob_idx] - w * h)
            
            overlap_indices = np.where(iou > iou_threshold)[0]
            
            origin_indices = idxs[overlap_indices]
            if len(overlap_indices) > 1:
                new_x = np.average(x1[origin_indices], weights=probs[origin_indices])
                new_y = np.average(y1[origin_indices], weights=probs[origin_indices])
                new_w = np.average(x2[origin_indices], weights=probs[origin_indices]) - new_x
                new_h = np.average(y2[origin_indices], weights=probs[origin_indices]) - new_y
                keep_going = True
            else:
                new_x, new_y, new_w, new_h = boxes[highest_prob_idx]
            
            new_boxes.append(np.array([new_x, new_y, new_w, new_h]))
            new_probs.append(np.mean(probs[origin_indices]))
            # delete all indexes from the index list that have iou greater than the
            # provided iou threshold
            idxs = np.delete(idxs, overlap_indices)
        
        boxes, probs = np.array(new_boxes), np.array(new_probs)
    
    for i in range(len(new_boxes)):
        x, y, w, h = new_boxes[i]
        if h / w > 1.3:
            x -= 5
            w += 10
        if h / w > 1.5:
            x -= 5
            w += 10
        # if h / w > 1.6:
        #     y += 8
        #     h -= 8
        new_boxes[i] = x, y, w, h
    
    new_boxes = np.maximum(0, new_boxes)
    return np.array(new_boxes, dtype='int'), new_probs

def get_cropped_images(regions, image, target_size=(32, 32), trim=False, plot_debug=False):
    region_images = []
    
    for i, (x, y, w, h) in enumerate(regions):
        cropped_image = image[y:y+h, x:x+w]
        # print(x,y,w,h)
        # plt.subplot('131')
        # plt.imshow(np.sort(cropped_image, axis=1))
        # if h / w > 1.5 and trim:
        #     x, y, w, h = regions[i]
        #     start_y = 0
        #     end_y = h
        #     trim_row = trim_row_index(cropped_image)
        #     if trim_row < h / 4:
        #         regions[i][1] += trim_row
        #         regions[i][3] -= trim_row
        #         cropped_image = cropped_image[trim_row:]
        #     elif trim_row > 0.75 * h:
        #         regions[i][3] = trim_row 
        #         cropped_image = cropped_image[:trim_row]
        # cropped_image = cv2.resize(cropped_image, target_size, interpolation=cv2.INTER_AREA)
        # region_images.append(cropped_image)
        if trim:
            # plt.subplot('121')
            # plt.imshow(cropped_image)
            if h / w > 1.5:
                cropped_image, new_box = trim_horizontally(cropped_image, regions[i])
                regions[i] = np.array(new_box)
                x, y, w, h = regions[i]
                # if h / w < 1.3:
                #     cropped_image, new_box = trim_vertically(cropped_image, regions[i])
                #     regions[i] = np.array(new_box)
            # elif w / image.shape[0] > 0.3 or h / w < 1.3: 
            #     cropped_image, new_box = trim_vertically(cropped_image, regions[i])
            #     regions[i] = np.array(new_box)
            #     x, y, w, h = regions[i]
            #     if h / w > 1.5:
            #         cropped_image, new_box = trim_horizontally(cropped_image, regions[i])
            #         regions[i] = np.array(new_box)
        
            # plt.subplot('122')
            # plt.imshow(cropped_image)
            # plt.show()
        cropped_image = cv2.resize(cropped_image, target_size, interpolation=cv2.INTER_AREA)
        region_images.append(cropped_image)
    
    return np.array(region_images), regions

def trim_horizontally(cropped_image, box):
    x, y, w, h = box
    start_y = 0
    end_y = h
    for _ in range(1):
        trim_row = trim_row_index(cropped_image)
        if trim_row + start_y < h / 4:
            # if trim_row + start_y < h / 8:
            #     continue
            start_y += trim_row
            cropped_image = cropped_image[trim_row:]
        elif trim_row + start_y > 0.75 * h:
            # if trim_row + start_y > 7/8 * h:
            #     continue
            end_y = start_y + trim_row
            cropped_image = cropped_image[:trim_row]
    
    return cropped_image, [x, y + start_y, w, end_y - start_y]

def trim_vertically(cropped_image, box):
    x, y, w, h = box
    start_x = 0
    end_x = w
    for _ in range(2):
        trim_col = trim_col_index(cropped_image)
        if trim_col + start_x < w / 4:
            # if trim_col + start_x < w / 10:
            #     print('not trim', trim_col + start_x, w / 10)
            #     continue
            # print('trim', trim_col)
            start_x += trim_col
            cropped_image = cropped_image[:, trim_col:]
        elif trim_col + start_x > 3/4 * w:
            # if trim_col + start_x > 9/10 * w:
            #     continue
            end_x = start_x + trim_col
            cropped_image = cropped_image[:, :trim_col]
    
    return cropped_image, [x + start_x, y, end_x - start_x, h]
    
def get_region_candidates(img):
    gray = clahe(img, clipLimit=3.0, tileGridSize=(10, 17))
    # # img = global_hist_equalize(img)
    # # img = thresh(img)
    # plt.subplot('411')
    # plt.imshow(img)
    # gray = convert_to_gray(img)
    
    mser = cv2.MSER_create(_delta=1)
    regions, _ = mser.detectRegions(gray)
    
    regions = [cv2.boundingRect(region.reshape(-1, 1, 2)) for region in regions]
    
    return np.array(regions)

def preprocess_images(images, mode):
    if mode == 'clf':
        mean = 107.524
        # mean = 103.93412087377622
        images = np.array([convert_to_gray(img) for img in images], dtype='float')
    elif mode == 'rcn':
        # mean = 112.833
        mean = 115.2230361178299
        # images = np.array([global_hist_equalize(img) for img in images], dtype='float')
        images = np.array([convert_to_gray(img) for img in images], dtype='float')
    
    images = images - mean
    
    if len(images.shape) < 4:
        images = images[..., None]
    
    return images

def trim_row_index(image):
    # if len(image.shape) > 2:
    #     image = convert_to_gray(image)[:,:,0]
    image = global_hist_equalize(image)
    
    h, w = image.shape[:2]
    row_mean = np.sort(image, axis=1)[:, -w//5:].mean(axis=1) 
    
    row_mask = row_mean > np.mean(row_mean)
    start = 0
    cnt = 0
    longest = 0
    for i in range(len(row_mask) - 1):
        if not row_mask[i]:
            cnt += 1
        elif row_mask[i]:
            if cnt > 0:
                if cnt > longest:
                    longest = cnt
                    start = i - cnt
                cnt = 0
    
    # print(start, longest, 'asdad')
    return start + longest // 2

def trim_col_index(image):
    # if len(image.shape) > 2:
    #     image = convert_to_gray(image)[:,:,0]
    image = global_hist_equalize(image)
    
    h, w = image.shape[:2]
    col_mean = np.sort(image, axis=0)[-h//6:].mean(axis=0) 
    
    col_mask = col_mean > np.mean(col_mean)
    start = 0
    cnt = 0
    longest = 0
    for i in range(len(col_mask) - 1):
        if not col_mask[i]:
            cnt += 1
        elif col_mask[i]:
            if cnt > 0:
                if cnt > longest:
                    longest = cnt
                    start = i - cnt
                cnt = 0
    
    # display_img = np.sort(image, axis=0)
    # print(start, longest, 'asdad')
    # cv2.line(display_img, (start + longest // 2, 0), (start + longest // 2, h), (255, 255, 255), 1)
    # plt.imshow(display_img)
    # plt.show()
    return start + longest // 2

def filt_boxes(boxes, image):
    keep_indices = []
    image_h, image_w = image.shape[:2]
    image_area = image_h * image_w
    for i, (x, y, w, h) in enumerate(boxes):
        # too small
        if image_w / w > 15:
            continue
        if image_h / h > 5:
            continue
        if image_area / (w * h) > 32:
            continue
        # too big
        if image_area / (w * h) < 5:
            continue
        # weird shape
        if w / h > 1.5 or h / w > 3:
            continue
        keep_indices.append(i)
    
    return boxes[keep_indices]

def get_rotate_angle(img, max_degree=10, plot_debug=False):
    img = bilateral_blur(img.copy(), 9, 50, 50)
    # img = sharpen(img)
    # plt.imshow(img)
    # plt.show()
    gray_img = clahe(img, clipLimit=2.0, tileGridSize=(21, 31))
    # gray_img = convert_to_gray(img)
    edges = cv2.Canny(gray_img, 50, 150, apertureSize=3)
    if plot_debug:
        plt.subplot('311')
        plt.imshow(edges)
    lines = cv2.HoughLinesP(image=edges, rho=1, theta=np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
    
    display_img = gray_img.copy()
    
    try:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0][0], line[0][1], line[0][2], line[0][3]
            if x2 - x1 > 30 and np.abs((y2 - y1) / (x2 - x1)) < np.tan(np.radians(max_degree)):
                angles.append(np.arctan((y2 - y1) / (x2 - x1)))
                if plot_debug:
                    cv2.line(display_img, (x1, y1), (x2, y2), (0, 0, 255), 3, cv2.LINE_AA)
        
        if len(angles) > 0:
            rotate_angle = np.mean(angles)
            rotate_angle = np.degrees(rotate_angle)
        else:
            rotate_angle = 0
    except Exception as e:
        rotate_angle = 0
    
    if plot_debug:
        plt.subplot('312')
        plt.imshow(display_img)
        print(rotate_angle)
        display_img = rotate(display_img, rotate_angle)
        plt.subplot('313')
        plt.imshow(display_img)
        plt.show()
    
    return rotate_angle

def get_red_blob_bounding_box(img, plot_debug=False):
    tmp = gamma_correct(img.copy())
    
    tmp = tmp[..., 2] - 0.5 * (tmp[..., 0] + tmp[..., 1])
    tmp -= np.min(tmp)
    tmp = tmp / np.max(tmp) * 255
    tmp = tmp.astype('uint8')
    
    pixel_values = np.sort(tmp.ravel())
    threshold = pixel_values[int(0.95 * len(pixel_values))]
    tmp = tmp * (tmp > threshold)
    
    tmp[:, :int(0.75 * tmp.shape[1])] = 0
    tmp[:int(0.1 * tmp.shape[0]), :] = 0
    tmp[-int(0.1 * tmp.shape[0]):, :] = 0
    
    contours, _ = cv2.findContours(tmp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2:]
    blob = max(contours, key=lambda el: cv2.contourArea(el))
    poly = cv2.approxPolyDP(blob, 3, True)
    x, y, w, h = cv2.boundingRect(poly)
    
    if plot_debug:
        cv2.rectangle(tmp, (x-5, y-5), (x+w+5, y+h+5), (255, 255, 255))
        plt.imshow(tmp)
        plt.show()
    
    return (x, y, w, h)

def read_cropped_image(origin_img, rcn_model, clf_model):
    img = origin_img.copy()

    rotate_angle = get_rotate_angle(img, max_degree=10)
    
    img = rotate(img, rotate_angle)
    origin_img = rotate(origin_img, rotate_angle)
    
    processed_img = clahe(img, clipLimit=3.0, tileGridSize=(10, 17))
    boxes = get_region_candidates(processed_img)
    boxes = filt_boxes(boxes, img)

    region_images, regions = get_cropped_images(boxes, bilateral_blur(img, 9, 50, 50), trim=False)

    processed_images = preprocess_images(region_images, mode='clf')
    probs = clf_model.predict_proba(processed_images, verbose=0)[:, 1]
    
    for i, (_, _, w, h) in enumerate(boxes):
        if h / w > 1.6 and h / w < 1.7:
            probs[i] += 0.1
        if h / w >= 1.75:
            probs[i] -= 0.1

    mask = probs > 0.4
    boxes = boxes[mask]
    region_images = region_images[mask]
    probs = probs[mask]

    boxes, probs = merge_boxes(boxes, probs)
    
    sort_indices = np.argsort(boxes[:, 0])
    boxes = np.array([boxes[i] for i in sort_indices])
    
    region_images, regions = get_cropped_images(boxes, img, trim=True)
    
    if len(region_images) > 0:
        processed_images = preprocess_images(region_images, mode='rcn')
        
        probs = rcn_model.predict_proba(processed_images)
        preds = probs.argmax(axis=-1)

        red_blob = get_red_blob_bounding_box(origin_img.copy())
        mean_w = np.mean([w for x, y, w, h in boxes])
        right_most = max(red_blob[0] - mean_w / 2, 0.8 * origin_img.shape[1])
        left_most = min(mean_w / 3, min([x for x, y, w, h in boxes]) - mean_w / 4)
        left_most = max(left_most, 0)
        width = right_most - left_most + 1
        
        prediction = [0, 0, 5, 5, 5]
        section_area = [0 for i in range(5)]
        for i, (x, y, w, h) in enumerate(boxes):
            section_idx = int((x + w / 2 - left_most) / (width / 5))
            if section_idx > 4:
                continue
            if w * h > section_area[section_idx]:
                prediction[section_idx] = preds[i]
                section_area[section_idx] = w * h
        
        if prediction[0] in [6, 8, 9]:
            prediction[0] = 0
        if prediction[1] in [6, 8, 9]:
            prediction[1] = 0
            
        prediction = ''.join([str(i) for i in prediction])
    else:
        prediction = '00555'
    
    return prediction, boxes
