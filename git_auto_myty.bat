@echo off
echo =================================
echo    MyTY �ֿ�Git�Զ����ű�
echo =================================
echo.

:: ����Ƿ���Git�ֿ��У�����������ʼ��
git status >nul 2>&1
if errorlevel 1 (
    echo MyTY�ֿ�δ��ʼ�������ڳ�ʼ��...
    git init
    echo ? Git�ֿ��ʼ�����
    echo.
    echo ��������Զ�ֿ̲⣨�����Ҫ��:
    echo git remote add origin [���myty�ֿ�URL]
    echo.
)

:: ��ʾ��ǰ״̬
git status
echo.

:: ����ļ����ݴ���
echo ����1: ����ļ����ݴ���...
git add .
if errorlevel 1 (
    echo ! ����ļ�ʱ��������
) else (
    echo ? ��ӳɹ�
)

echo.

:: �ύ����
echo ����2: �ύ����...
git commit -m "����myty�ֿ�" --allow-empty
if errorlevel 1 (
    echo ! �ύ����û�б仯
) else (
    echo ? �ύ�ɹ�
)

echo.

:: ����Ƿ���Զ�ֿ̲�����
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo ��ʾ: δ����Զ�ֿ̲⣬����pull/push����
    echo ��������Զ�ֿ̲⣬������: git remote add origin [�ֿ�URL]
) else (
    :: ��ȡԶ�̸���
    echo ����3: ��ȡԶ�̸���...
    git pull origin main --allow-unrelated-histories --no-edit
    if errorlevel 1 (
        echo ! ��ȡʧ�ܣ�����ʹ��master��֧...
        git pull origin master --allow-unrelated-histories --no-edit
    )
    echo ? ��ȡ�ɹ�
    
    echo.
    
    :: ���͵�Զ�ֿ̲�
    echo ����4: ���͵�Զ�ֿ̲�...
    git push origin main
    if errorlevel 1 (
        echo ! ���͵�main��֧ʧ�ܣ�����master��֧...
        git push origin master
    )
    echo ? ���ͳɹ�
)

echo.
echo =================================
echo   MyTY�ֿ�������!
echo =================================
echo.
pause