function evaluate_model()
% EVALUATE_MODEL Tests trained model and shows confusion matrix

    root = fileparts(fileparts(mfilename('fullpath')));
    model_path = fullfile(root, 'models', 'face_recognition_model.mat');

    if ~exist(model_path, 'file')
        error('Model not found. Run train_model() first.');
    end

    disp('Loading model...');
    loaded = load(model_path);
    net = loaded.net;
    class_names = loaded.class_names;

    % Reload validation data
    [~, aug_val, ~] = preprocess_data();

    disp('Running predictions on validation set...');
    predicted_labels = classify(net, aug_val, ...
        'ExecutionEnvironment', 'cpu', ...
        'MiniBatchSize', 16);

    % Get true labels
    image_dir = fullfile(root, 'data', 'student_images');
    imds = imageDatastore(image_dir, ...
        'IncludeSubfolders', true, ...
        'LabelSource', 'foldernames');
    [~, val_imds] = splitEachLabel(imds, 0.8, 'randomized');
    true_labels = val_imds.Labels;

    % Accuracy
    accuracy = mean(predicted_labels == true_labels) * 100;
    fprintf('\nValidation Accuracy: %.2f%%\n', accuracy);

    % Confusion matrix
    figure;
    cm = confusionchart(true_labels, predicted_labels);
    cm.Title = sprintf('Face Recognition — Accuracy: %.2f%%', accuracy);
    cm.RowSummary = 'row-normalized';
    cm.ColumnSummary = 'column-normalized';

    disp('Evaluation complete.');
end