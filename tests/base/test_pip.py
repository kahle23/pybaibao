import subprocess

import pytest
from unittest.mock import patch, MagicMock
from baibao.base.pip import install, _install_single, DEFAULT_MIRRORS


class TestInstallSingle:
    """测试 _install_single 内部方法"""

    @patch('baibao.base.pip.subprocess.run')
    def test_install_single_success_first_mirror(self, mock_run):
        """测试第一个镜像安装成功"""
        mock_run.return_value.returncode = 0

        success, msg = _install_single('requests')

        assert success is True
        assert DEFAULT_MIRRORS[0] in msg
        mock_run.assert_called_once()

    @patch('baibao.base.pip.subprocess.run')
    def test_install_single_fail_first_success_second(self, mock_run):
        """测试第一个镜像失败，第二个镜像成功"""
        mock_run.side_effect = [
            Exception("Connection refused"),
            MagicMock(returncode=0)
        ]

        success, msg = _install_single('requests')

        assert success is True
        assert DEFAULT_MIRRORS[1] in msg
        assert mock_run.call_count == 2

    @patch('baibao.base.pip.subprocess.run')
    def test_install_single_all_mirrors_fail(self, mock_run):
        """测试所有镜像都失败"""
        mock_run.side_effect = Exception("Connection refused")

        success, msg = _install_single('requests')

        assert success is False
        assert "所有镜像站点安装失败" in msg
        assert mock_run.call_count == len(DEFAULT_MIRRORS)

    @patch('baibao.base.pip.subprocess.run')
    def test_install_single_timeout(self, mock_run):
        """测试安装超时"""
        mock_run.side_effect = [
            subprocess.TimeoutExpired(cmd=['python', '-m', 'pip'], timeout=60),
            MagicMock(returncode=0)
        ]

        success, msg = _install_single('requests', timeout=60)

        assert success is True
        assert DEFAULT_MIRRORS[1] in msg

    @patch('baibao.base.pip.subprocess.run')
    def test_install_single_with_custom_mirrors(self, mock_run):
        """测试使用自定义镜像列表"""
        custom_mirrors = ['https://custom-mirror.com/simple/']
        mock_run.return_value.returncode = 0

        success, msg = _install_single('requests', mirrors=custom_mirrors)

        assert success is True
        assert custom_mirrors[0] in msg
        mock_run.assert_called_once()

    @patch('baibao.base.pip.subprocess.run')
    def test_install_single_with_version(self, mock_run):
        """测试安装指定版本的包"""
        mock_run.return_value.returncode = 0

        success, msg = _install_single('requests==2.31.0')

        assert success is True
        assert 'requests==2.31.0' in msg


class TestInstall:
    """测试 install 公开方法"""

    @patch('baibao.base.pip._install_single')
    def test_install_single_package(self, mock_install_single):
        """测试安装单个包（字符串）"""
        mock_install_single.return_value = (True, "success")

        result = install('requests')

        assert isinstance(result, tuple)
        assert result[0] is True
        mock_install_single.assert_called_once_with('requests', 120, None)

    @patch('baibao.base.pip._install_single')
    def test_install_multiple_packages_all_success(self, mock_install_single):
        """测试批量安装所有包成功"""
        mock_install_single.return_value = (True, "success")

        success_list, fail_list = install(['requests', 'pandas'])

        assert success_list == ['requests', 'pandas']
        assert fail_list == []
        assert mock_install_single.call_count == 2

    @patch('baibao.base.pip._install_single')
    def test_install_multiple_packages_partial_success(self, mock_install_single):
        """测试批量安装部分成功"""
        mock_install_single.side_effect = [
            (True, "success"),
            (False, "fail")
        ]

        success_list, fail_list = install(['requests', 'nonexistent-package'])

        assert success_list == ['requests']
        assert len(fail_list) == 1
        assert 'nonexistent-package' in fail_list[0]

    @patch('baibao.base.pip._install_single')
    def test_install_empty_list(self, mock_install_single):
        """测试安装空列表"""
        success_list, fail_list = install([])

        assert success_list == []
        assert fail_list == []
        mock_install_single.assert_not_called()

    @patch('baibao.base.pip._install_single')
    def test_install_with_custom_timeout(self, mock_install_single):
        """测试使用自定义超时时间"""
        mock_install_single.return_value = (True, "success")

        install('requests', timeout=60)

        mock_install_single.assert_called_once_with('requests', 60, None)

    @patch('baibao.base.pip._install_single')
    def test_install_with_custom_mirrors(self, mock_install_single):
        """测试使用自定义镜像列表"""
        custom_mirrors = ['https://custom.com/simple/']
        mock_install_single.return_value = (True, "success")

        install('requests', mirrors=custom_mirrors)

        mock_install_single.assert_called_once_with('requests', 120, custom_mirrors)

    @patch('baibao.base.pip._install_single')
    def test_install_multiple_with_mirrors(self, mock_install_single):
        """测试批量安装时传递自定义镜像"""
        custom_mirrors = ['https://custom.com/simple/']
        mock_install_single.return_value = (True, "success")

        install(['a', 'b'], mirrors=custom_mirrors)

        calls = mock_install_single.call_args_list
        for call in calls:
            assert call[0][2] == custom_mirrors