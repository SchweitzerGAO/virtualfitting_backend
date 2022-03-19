import os
import shutil
from flask import Flask, render_template, send_from_directory, request, jsonify, make_response
import time
from flask_cors import CORS

app = Flask(__name__)

CORS(app, resources=r'/*')  # 解决可能存在的跨域问题

UPLOAD_FOLDER = 'upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # 设置文件上传的目标文件夹
app.config['MODEL_PATH'] = 'D:\项目\virtual-fitting\smplify-x-master\output\meshes'

basedir = os.path.abspath(os.path.dirname(__file__))  # 获取当前项目的绝对路径
ALLOWED_EXTENSIONS = {'png', 'jpg', 'JPG', 'PNG'}  # 允许上传的文件后缀
work_path = 'D:/项目/virtual-fitting/smplify-x-master'  # 工作路径，换成你电脑（最终要换成服务器上相应的）smplifyx所在的路径, 下同
data_path = 'D:/项目/virtual-fitting/smplify-x-master/data'  # 数据总文件夹
image_path = 'D:/项目/virtual-fitting/smplify-x-master/data/images'  # 用户图片文件夹
keypoint_path = 'D:/项目/virtual-fitting/smplify-x-master/data/keypoints'  # 关节信息文件夹

file_name = ''

files = []

# docker 容器ID
docker_container_id = 'bd05c03ea4a4'
docker_container_long_id = 'bd05c03ea4a47e14b383d08e783c9ec81bfdb6f98d7fb2659cab2f2395fa2f9b'


# 判断文件是否合法
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# 清空data文件夹，将用户的照片移动到data/images中
def mov_photo(src, tar=image_path):
    if not os.path.exists(data_path):
        os.mkdir(data_path)
    else:
        shutil.rmtree(data_path)
        os.mkdir(data_path)
    os.mkdir(image_path)
    try:
        shutil.copy(src, tar)
    except IOError:
        print('Unable to copy file')


# 服务器端利用docker容器生成关键点
def generate_keypoints_docker():
    # 获取上传的文件
    global files
    files = os.listdir('./upload')
    # 清空之前的文件，加快重建速度
    os.system('docker exec ' + docker_container_id + ' /bin/bash -c \'rm -rf ./images && mkdir ./images\'')
    os.system('docker exec ' + docker_container_id + ' /bin/bash -c \'rm -rf ./keypoints && mkdir ./keypoints\'')
    # 将主机上用户的照片传到docker容器中
    os.system(
        'docker cp ./upload/' + files[0] + ' ' + docker_container_long_id + ':/openpose-master/images/' + files[0])
    # 执行openpose 关键点提取
    os.system(
        'docker exec ' + docker_container_id + '/bin/bash -c \'./build/examples/openpose/openpose.bin --image_dir '
                                               './images/ --write_json ./keypoints/\'')
    # 清理，重建data文件夹
    os.system('rm -rf ../data && mkdir ../data/images')

    # 将生成的关键点送回主机
    os.system('docker cp ' + docker_container_long_id + ':/openpose-master/keypoints/ ../data/keypoints')


# 服务器端人体重建
def generate_model_docker():
    # 激活conda环境
    os.system('conda activate smplify-x')

    # 清理output文件夹
    os.system('rm -rf ../output && mkdir ../output')
    # 进行模型重建
    os.system("python ../smplifyx/main.py --config cfg_files/fit_smplx.yaml --data_folder ../data --output_folder "
              "../output "
              "--visualize='False' --model_folder ../models --vposer_ckpt ../vposer_v1_0 --part_segm_fn "
              "../smplx_parts_segm.pkl")


@app.route('/api/docker/get/model', methods=['GET'])
def get_model_docker():
    generate_keypoints_docker()
    generate_model_docker()
    return jsonify({"code": 200, "msg": '模型重建成功'})


'''下面的生成关键点和生成模型的都原内容写到生成文件的api里面了，没有调用，这里只是方便调试和方便明白两部分的代码功能'''


# 生成关键点
def generate_keypoints():
    os.chdir("D:/项目/virtual-fitting/openpose-gpu")
    print('processing.wait for seconds')
    os.system(
        "bin\\OpenPoseDemo.exe --image_dir D:\\项目\\virtual-fitting\\smplify-x-master\\data\\images --hand --face "
        "--write_json D:\\项目\\virtual-fitting\\smplify-x-master\\data\\keypoints")
    print('generate_keypoints:done')


# 生成模型
def generate_model():
    os.system("conda activate virtual_fit")
    os.chdir("D:/项目/virtual-fitting/smplify-x-master")
    print('processing.This may take a few minutes')
    os.system(
        "python smplifyx/main.py --config cfg_files/fit_smplx.yaml --data_folder ./data --output_folder ./output "
        "--visualize='False' --model_folder ./models --vposer_ckpt ./vposer_v1_0 --part_segm_fn smplx_parts_segm.pkl")
    print('generate_model:done')


# @app.route('/api/generate')
# def api_generate():
#     generate_keypoints()
#     generate_model()

#     return jsonify({"code": 200, "msg": "生成成功"})


# file_name是客户端传来的需要下载的文件名
# @app.route('/api/get_file/<file_name>', methods=['GET'])
@app.route('/api/get_file', methods=['GET'])
def get_file():
    try:
        os.chdir("D:/项目/virtual-fitting/openpose-gpu")
        print('processing.wait for seconds')
        os.system(
            "bin\\OpenPoseDemo.exe --image_dir D:\\项目\\virtual-fitting\\smplify-x-master\\data\\images --hand --face --write_json D:\\项目\\virtual-fitting\\smplify-x-master\\data\\keypoints")
        print('generate_keypoints:done')

        os.system("conda activate virtual_fit")
        os.chdir("D:/项目/virtual-fitting/smplify-x-master")
        print('processing.This may take a few minutes')
        os.system(
            "python smplifyx/main.py --config cfg_files/fit_smplx.yaml --data_folder ./data --output_folder ./output --visualize='False' --model_folder ./models --vposer_ckpt ./vposer_v1_0 --part_segm_fn smplx_parts_segm.pkl")
        print('generate_model:done')

        # 需要修改！
        global file_name
        path = 'D:\项目\\virtual-fitting\smplify-x-master\output\meshes\\' + file_name + '\\000.obj'
        path = 'D:\项目\\virtual-fitting\smplify-x-master\output\meshes\\' + '1' + '\\000.obj'
        # fp = open(path, mode='r')
        # return fp

        return send_from_directory('D:\项目\\virtual-fitting\smplify-x-master\output\meshes\\1', '000.obj',
                                   as_attachment=True)  # as_attachment=True  下载
        # return path
    except Exception:
        return jsonify({"code": 500, "msg": "模型生成error"})


# 具有上传功能的页面
@app.route('/')
def upload_test():
    return render_template('upload.html')


@app.route('/api/upload', methods=['POST'], strict_slashes=False)
def api_upload():
    file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'])  # 拼接成合法文件夹地址
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)  # 文件夹不存在就创建
    f = request.files.get('file')  # 从表单的file字段获取文件，myfile为该表单的name值
    if f and allowed_file(f.filename):  # 判断是否是允许上传的文件类型
        fname = f.filename
        global file_name
        file_name = fname
        ext = fname.rsplit('.', 1)[1]  # 获取文件后缀
        unix_time = int(time.time())
        new_filename = str(unix_time) + '.' + ext  # 修改文件名
        save_filename = os.path.join(file_dir, new_filename)
        f.save(save_filename)  # 保存文件到upload目录
        mov_photo(save_filename, tar='../data/images/')  # 复制照片到smplify-x相应目录下
        return jsonify({"code": 200, "msg": "上传成功"})
    else:
        return jsonify({"code": 400, "msg": "文件格式不正确"})


# 下载文件（暂时用不到）
@app.route("/api/download", methods=['GET'])
def downloader():
    dirpath = '../output/meshes/'+files[0]
    return send_from_directory(dirpath, '000.obj', as_attachment=True)  # as_attachment=True  下载


if __name__ == '__main__':
    app.run(debug=True)
