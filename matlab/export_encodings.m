function export_encodings()
% EXPORT_ENCODINGS Extracts face encodings from trained model and saves to CSV

    root = fileparts(fileparts(mfilename('fullpath')));
    model_path = fullfile(root, 'models', 'face_recognition_model.mat');

    if ~exist(model_path, 'file')
        error('Model not found. Run train_model() first.');
    end

    disp('Loading model...');
    loaded = load(model_path);
    net = loaded.net;

    % Load all student images
    image_dir = fullfile(root, 'data', 'student_images');
    imds = imageDatastore(image_dir, ...
        'IncludeSubfolders', true, ...
        'LabelSource', 'foldernames');

    disp('Extracting feature encodings...');

    % Extract features from the last FC layer before classification
    features = activations(net, imds, 'fc7', ...
        'MiniBatchSize', 16, ...
        'OutputAs', 'rows', ...
        'ExecutionEnvironment', 'cpu');

    labels = cellstr(imds.Labels);

    % Build table and save
    feature_table = array2table(features);
    feature_table.student_id = labels;

    % Move student_id to first column
    feature_table = [feature_table(:,end), feature_table(:,1:end-1)];

    output_path = fullfile(root, 'models', 'face_encodings.csv');
    writetable(feature_table, output_path);

    fprintf('Encodings saved: %d rows x %d features\n', ...
        height(feature_table), width(feature_table)-1);
    disp(['Saved to: ', output_path]);
end