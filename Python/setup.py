from distutils.core import setup
setup(name='load_intan_rhd_format',
      version='1.0',
      py_modules=['load_intan_rhd_format', 'intanutil.data_to_result',
                  'intanutil.read_header',
                  'intanutil.get_bytes_per_data_block',
                  'intanutil.read_one_data_block', 'intanutil.notch_filter',
                  'intanutil.qstring'],
      author='Michael Gibson',
      author_email='info@intan.com',
      url='http://intantech.com'
      )
