#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PipUtil 的测试类
"""

from unittest.mock import MagicMock, patch

import subprocess

from baibao.base import PipUtil


class TestPipUtilDefaultMirrors:
    """PipUtil 默认镜像测试"""

    def test_default_mirrors_exist(self):
        """测试默认镜像列表存在且非空"""
        assert PipUtil.DEFAULT_MIRRORS is not None
        assert len(PipUtil.DEFAULT_MIRRORS) > 0
        assert 'https://pypi.org/simple/' in PipUtil.DEFAULT_MIRRORS

    def test_python_command_default(self):
        """测试默认 Python 命令"""
        assert PipUtil.PYTHON_COMMAND == 'python'


class TestPipUtilInstallSingle:
    """_install_single 静态方法测试"""

    @patch('baibao.base.pip_util.subprocess.run')
    def test_install_single_success_first_mirror(self, mock_run):
        """测试使用第一个镜像成功安装"""
        mock_run.return_value = MagicMock(returncode=0)

        success, msg = PipUtil._install_single('requests', timeout=30)

        assert success is True
        assert '成功使用镜像' in msg
        assert 'requests' in msg
        mock_run.assert_called_once()

    @patch('baibao.base.pip_util.subprocess.run')
    def test_install_single_success_second_mirror(self, mock_run):
        """测试第一个镜像失败后使用第二个镜像成功安装"""
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, 'pip', stderr='error'),
            MagicMock(returncode=0)
        ]

        success, msg = PipUtil._install_single('requests', timeout=30)

        assert success is True
        assert '成功使用镜像' in msg
        assert mock_run.call_count == 2

    @patch('baibao.base.pip_util.subprocess.run')
    def test_install_single_all_mirrors_fail(self, mock_run):
        """测试所有镜像都失败"""
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, 'pip', stderr='error1'),
            subprocess.CalledProcessError(1, 'pip', stderr='error2'),
            subprocess.CalledProcessError(1, 'pip', stderr='error3'),
            subprocess.CalledProcessError(1, 'pip', stderr='error4')
        ]

        success, msg = PipUtil._install_single('requests', timeout=30)

        assert success is False
        assert '所有镜像站点安装失败' in msg
        assert mock_run.call_count == 4

    @patch('baibao.base.pip_util.subprocess.run')
    def test_install_single_timeout(self, mock_run):
        """测试安装超时"""
        mock_run.side_effect = subprocess.TimeoutExpired('pip', 30)

        success, msg = PipUtil._install_single('requests', timeout=30)

        assert success is False
        assert '超时' in msg

    @patch('baibao.base.pip_util.subprocess.run')
    def test_install_single_with_version(self, mock_run):
        """测试安装指定版本的包"""
        mock_run.return_value = MagicMock(returncode=0)

        success, msg = PipUtil._install_single('requests==2.31.0', timeout=30)

        assert success is True
        assert 'requests==2.31.0' in msg

    @patch('baibao.base.pip_util.subprocess.run')
    def test_install_single_with_custom_mirrors(self, mock_run):
        """测试使用自定义镜像列表"""
        mock_run.return_value = MagicMock(returncode=0)
        custom_mirrors = ['https://custom.mirror.com/simple/']

        success, msg = PipUtil._install_single('requests', timeout=30, mirrors=custom_mirrors)

        assert success is True
        assert 'https://custom.mirror.com/simple/' in msg
        mock_run.assert_called_once()

    @patch('baibao.base.pip_util.subprocess.run')
    def test_install_single_exception_handling(self, mock_run):
        """测试异常处理"""
        mock_run.side_effect = Exception('Unexpected error')

        success, msg = PipUtil._install_single('requests', timeout=30)

        assert success is False
        assert '发生异常' in msg


class TestPipUtilInstall:
    """install 静态方法测试"""

    @patch.object(PipUtil, '_install_single')
    def test_install_single_package(self, mock_install_single):
        """测试安装单个包"""
        mock_install_single.return_value = (True, 'success')

        result = PipUtil.install('requests')

        assert result == (True, 'success')
        mock_install_single.assert_called_once()

    @patch.object(PipUtil, '_install_single')
    def test_install_multiple_packages_all_success(self, mock_install_single):
        """测试批量安装全部成功"""
        mock_install_single.side_effect = [
            (True, 'success1'),
            (True, 'success2')
        ]

        success_list, fail_list = PipUtil.install(['requests', 'numpy'])

        assert success_list == ['requests', 'numpy']
        assert fail_list == []
        assert mock_install_single.call_count == 2

    @patch.object(PipUtil, '_install_single')
    def test_install_multiple_packages_mixed(self, mock_install_single):
        """测试批量安装部分成功"""
        mock_install_single.side_effect = [
            (True, 'success'),
            (False, 'failed'),
            (True, 'success')
        ]

        success_list, fail_list = PipUtil.install(['requests', 'nonexistent', 'numpy'])

        assert success_list == ['requests', 'numpy']
        assert len(fail_list) == 1
        assert 'nonexistent' in fail_list[0]

    @patch.object(PipUtil, '_install_single')
    def test_install_with_custom_timeout(self, mock_install_single):
        """测试自定义超时时间"""
        mock_install_single.return_value = (True, 'success')

        result = PipUtil.install('requests', timeout=60)

        assert result == (True, 'success')

    @patch.object(PipUtil, '_install_single')
    def test_install_with_custom_mirrors(self, mock_install_single):
        """测试使用自定义镜像列表"""
        mock_install_single.return_value = (True, 'success')
        custom_mirrors = ['https://custom.mirror.com/simple/']

        PipUtil.install('requests', mirrors=custom_mirrors)

        # 验证自定义镜像被传递到 _install_single（位置参数）
        call_args = mock_install_single.call_args
        assert call_args[0][0] == 'requests'
        assert call_args[0][2] == custom_mirrors


class TestPipUtilCommandConstruction:
    """命令构建测试"""

    @patch('baibao.base.pip_util.subprocess.run')
    def test_command_construction(self, mock_run):
        """测试 pip 命令构建正确"""
        mock_run.return_value = MagicMock(returncode=0)

        PipUtil._install_single('requests', timeout=30)

        call_args = mock_run.call_args[0][0]
        assert call_args[:4] == ['python', '-m', 'pip', 'install']
        assert 'requests' in call_args
        assert '-i' in call_args
        assert '--trusted-host' in call_args

    @patch('baibao.base.pip_util.subprocess.run')
    def test_command_with_custom_python(self, mock_run):
        """测试自定义 Python 命令"""
        mock_run.return_value = MagicMock(returncode=0)
        original_python = PipUtil.PYTHON_COMMAND

        try:
            PipUtil.PYTHON_COMMAND = 'python3'
            PipUtil._install_single('requests', timeout=30)

            call_args = mock_run.call_args[0][0]
            assert call_args[0] == 'python3'
        finally:
            PipUtil.PYTHON_COMMAND = original_python
