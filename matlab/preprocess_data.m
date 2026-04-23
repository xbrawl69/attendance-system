function [aug_train, aug_val, class_names] = preprocess_data()
% PREPROCESS_DATA Loads images and prepares augmented train/val datastores

    root = fileparts(fileparts(mfilename('fullpath')));
    image_dir = fullfile(root, 'data', 'student_images');

    disp('Loading image datastore...');
    imds = imageDatastore(image_dir, ...
        'IncludeSubfolders', true, ...
        'LabelSource', 'foldernames');

    % Check minimum images per class
    label_count = countEachLabel(imds);
    disp('Images per student:');
    disp(label_count);

    min_count = min(label_count.Count);
    if min_count < 10
        warning('Some students have fewer than 10 images. Capture more for better accuracy.');
    end

    % Split 80% train, 20% validation
    [train_imds, val_imds] = splitEachLabel(imds, 0.8, 'randomized');

    class_names = categories(imds.Labels);
    disp(['Total students (classes): ', num2str(numel(class_names))]);
    disp(['Training images  : ', num2str(numel(train_imds.Files))]);
    disp(['Validation images: ', num2str(numel(val_imds.Files))]);

    % Augmentation for training (helps with limited images)
    aug_ops = imageDataAugmenter(...
        'RandXReflection',   true, ...
        'RandRotation',      [-15, 15], ...
        'RandXScale',        [0.9, 1.1], ...
        'RandYScale',        [0.9, 1.1], ...
        'RandXTranslation',  [-10, 10], ...
        'RandYTranslation',  [-10, 10], ...
        'RandXShear',        [-5, 5], ...
        'RandYShear',        [-5, 5]);

    aug_train = augmentedImageDatastore([227 227 3], train_imds, ...
        'DataAugmentation', aug_ops);

    % Validation — no augmentation, just resize
    aug_val = augmentedImageDatastore([227 227 3], val_imds);

    disp('Preprocessing complete.');
end