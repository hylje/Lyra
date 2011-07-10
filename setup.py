from distutils.core import setup

setup(name='lyra',
      version='1.2',
      description='time management app for django',
      author='Leo Honkanen',
      author_email='leo.o.honkanen@gmail.com',
      url='https://github.com/hylje/lyra',
      packages=['lyra', 
                'lyra.contrib',
                'lyra.contrib.duty',
                'lyra.contrib.food',
                'lyra.contrib.drive',])
