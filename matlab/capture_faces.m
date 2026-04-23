function capture_faces(student_id, num_images)
% CAPTURE_FACES Captures face images from webcam for a given student
% Usage: capture_faces('STU001', 50)

    if nargin < 2
        num_images = 50;
    end

    % Build save path
    root = fileparts(fileparts(mfilename('fullpath')));
    save_dir = fullfile(root, 'data', 'student_images', student_id);

    if ~exist(save_dir, 'dir')
        mkdir(save_dir);
    end

    % Start webcam
    cam = webcam(1);
    cam.Resolution = '640x480';

    face_detector = vision.CascadeObjectDetector();
    face_detector.MergeThreshold = 4;

    disp('=== Face Capture Started ===');
    disp(['Student ID : ', student_id]);
    disp(['Saving to  : ', save_dir]);
    disp('Look at the camera. Move your head slightly for variety.');
    disp('Press Ctrl+C to stop early.');

    count = 0;

    while count < num_images
        frame = snapshot(cam);
        bboxes = step(face_detector, frame);

        if ~isempty(bboxes)
            % Take the largest detected face
            [~, idx] = max(bboxes(:,3) .* bboxes(:,4));
            bbox = bboxes(idx, :);

            % Add padding around face
            pad = 20;
            x = max(1, bbox(1) - pad);
            y = max(1, bbox(2) - pad);
            w = min(size(frame,2) - x, bbox(3) + 2*pad);
            h = min(size(frame,1) - y, bbox(4) + 2*pad);

            face_crop = imcrop(frame, [x y w h]);
            face_resized = imresize(face_crop, [227 227]);

            count = count + 1;
            filename = fullfile(save_dir, sprintf('img_%03d.jpg', count));
            imwrite(face_resized, filename);

            % Show progress
            imshow(face_resized);
            title(sprintf('Captured %d / %d — Student: %s', count, num_images, student_id));
            drawnow;

            pause(0.3);
        else
            disp('No face detected — adjust position...');
            pause(0.2);
        end
    end

    clear cam;
    close all;
    disp(['Done! ', num2str(count), ' images saved to: ', save_dir]);
end