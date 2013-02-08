# -*- coding: utf-8 -*-

#===============================================================================
# Created on Nov 12, 2012
# 
# @author: bertrand Néron
# @contact: bneron <at> pasteur <dot> fr
# @organization: organization_name
# @license: license
#===============================================================================

import os
import sys
import inspect
from time import strftime
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

_prefix_path = '$PREFIX'
if os.environ['TXSSCAN_HOME']:
    _prefix_path = os.environ['TXSSCAN_HOME']


import logging

class Config(object):
    """
    parse configuration files and handle the configuration according the file location precedence
    /etc/txsscan/txsscan.conf < ~/.txsscan/txsscan.conf < .txsscan.conf
    if a configuration file is given on the command line, only this file is used.
    in fine the arguments passed have the highest priority
    """
    
    #if a new option is added think to add it also (if needed) in save
    options = ( 'cfg_file', 'previous_run', 'sequence_db', 'db_type', 'replicon_topology', 'hmmer_exe' , 'e_value_res', 'i_evalue_sel', 'coverage_profile', 
               'def_dir', 'res_search_dir', 'res_search_suffix', 'profile_dir', 'profile_suffix', 'res_extract_suffix', 
               'log_level', 'log_file', 'worker_nb', 'config_file')

    def __init__(self, cfg_file = "",
                sequence_db = None ,
                db_type = None,
                replicon_topology = None,
                hmmer_exe = None,
                e_value_res = None,
                i_evalue_sel = None,
                coverage_profile = None,
                def_dir = None ,
                res_search_dir = None,
                res_search_suffix = None,
                profile_dir = None,
                profile_suffix = None,
                res_extract_suffix = None,
                log_level = None,
                log_file = None,
                worker_nb = None,
                config_file = None,
                previous_run = None
                ):
        """
        :param cfg_file: the path of txsscan configuration file to use 
        :type cfg_file: string
        :param previous_run: the path of the directory of a previous run
        :type previous_run: string 
        :param sequence_db: the path to the sequence database
        :type sequence_db: string
        :param db_type: the type of genes base 4 values are allowed ('unordered_replicon', 'ordered_replicon', 'gembase', 'unordered') 
        :type db_type: string
        :param replicon_topology: the topology ('linear' or 'circular') of the replicons. This option is meaningfull only if the db_type is 'ordered_replicon' or 'gembase' 
        :type replicon_topology: string
        :param hmmer_exe: the hmmsearch executabe
        :type hmmer_exe: string
        :param e_value_res: à déterminer
        :type  e_value_res: float
        :param i_evalue_sel: à déterminer
        :type  i_evalue_sel: float
        :param coverage_profile: a déterminer
        :type coverage_profile: float
        :param def_dir: the path to the definition directory
        :type def_dir: string
        :param res_search_dir: à déterminer
        :type  res_search_dir: string
        :param res_search_suffix: à déterminer
        :type  res_search_suffix: string
        :param res_extract_suffix: à déterminer
        :type  res_extract_suffix: string
        :param profile_dir: à déterminer
        :type  profile_dir: string
        :param profile_suffix: à déterminer
        :type  profile_suffix: string
        :param log_level: the level of log output
        :type log_level: int
        :param log_file: the path of file to write logs 
        :type log_file: string
        :param worker_nb: the max number of processes in parrallel
        :type worker_nb: int
        """
        
        self._new_cfg_name = "txsscan.conf"
        if previous_run:
            prev_config = os.path.join(previous_run, self._new_cfg_name)
            if not os.path.exists(prev_config):
                raise ValueError("No config file found in dir %s" % previous_run)
            config_files = [prev_config]
        elif cfg_file:
            config_files = [cfg_file]
        else:
            config_files = [os.path.join(_prefix_path, '/etc/txsscan/txsscan.conf'),
                           os.path.expanduser('~/.txsscan/txsscan.conf'),
                           '.txsscan.conf']
        self._defaults = {'replicon_topology': 'linear',
                          'hmmer_exe' : 'hmmsearch',
                          'e_value_res' : "1",
                          'i_evalue_sel' : "0.5",
                          'coverage_profile' : "0.5",
                          'def_dir': './DEF',
                          'res_search_dir' : './datatest/res_search',
                          'res_search_suffix' : '.search_hmm.out',
                          'res_extract_suffix' : '.res_hmm_extract',
                          'profile_dir' : './profiles',
                          'profile_suffix' : '.fasta-aln_edit.hmm', 
                          'log_level': '0',
                          'worker_nb' : '0'
                          }
        self.parser = SafeConfigParser(defaults= self._defaults)
        used_files = self.parser.read(config_files)

        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)

        cmde_line_opt = {}
        for arg in args:
            if arg in self.options and values[arg] is not None:
                #the option in ConfigParser are store as string
                #so in save method I dump some options only if 
                #they are != than the default values in ConfigParser
                cmde_line_opt[arg] = str(values[arg])

        self.options = self._validate(cmde_line_opt)        

    def _validate(self, cmde_line_opt):
        """
        get all configuration values and validate the values
        create the working directory

        :param cmde_line_opt: the options from the command line
        :type cmde_line_opt: dict
        :return: all the options for this execution
        :rtype: dictionnary
        """  
        options = {}
        if 'sequence_db' in cmde_line_opt:
            cmde_line_opt['file'] = cmde_line_opt['sequence_db']

        try:      
            options['res_search_dir'] = self.parser.get('directories', 'res_search_dir', vars = cmde_line_opt)
        except NoSectionError:
            if 'res_search_dir' in cmde_line_opt:
                options['res_search_dir'] = cmde_line_opt['res_search_dir']
            else:
                options['res_search_dir'] = self._defaults['res_search_dir']
        if not os.path.exists(options['res_search_dir']):
            raise ValueError( "%s: No such research search directory" % options['res_search_dir'])
        if not os.access(options['res_search_dir'], os.W_OK):
            raise ValueError("research search directory (%s) is not writable" % options['res_search_dir'])

        working_dir = os.path.join(options['res_search_dir'], "txsscan-" + strftime("%Y%m%d_%H-%M-%S"))
        try:
            os.mkdir(working_dir)
        except OSError, err:
            raise ValueError("cannot create working directory %s : %s" % (working_dir, err))
        options['working_dir'] = working_dir

        try:
            log_level = self.parser.get('general', 'log_level', vars = cmde_line_opt)
        except (AttributeError, NoSectionError):
            log_level = logging.ERROR
        else:
            try:
                log_level = int(log_level)
            except ValueError:
                try:
                    log_level = getattr(logging, log_level.upper())
                except AttributeError:
                    log_level = logging.ERROR
        options['log_level'] = log_level
        
        log_error = []            
        try:
            log_file = self.parser.get('general', 'log_file', vars = cmde_line_opt)
            log_handler = logging.FileHandler(log_file)
            options['log_file'] = log_file
        except Exception , err:
            if not isinstance(err, NoOptionError):
                log_error.append(err)
            try:
                log_file = os.path.join( options['working_dir'], 'txsscan.log' )
                log_handler = logging.FileHandler(log_file)
                options['log_file'] = log_file
            except Exception , err:
                log_error.append(err)
                log_handler = logging.StreamHandler(sys.stderr)
                options['log_file'] = ''
        
        handler_formatter = logging.Formatter("%(levelname)-8s : %(filename)-10s : L %(lineno)d : %(asctime)s : %(message)s")
        log_handler.setFormatter(handler_formatter)
        log_handler.setLevel(log_level)

        root = logging.getLogger()
        root.setLevel( logging.NOTSET )

        logger = logging.getLogger('txsscan')
        logger.setLevel(log_level)
        logger.addHandler(log_handler)

        self._log = logging.getLogger('txsscan.config')
        for error in log_error:
            self._log.warn(error)
        try:
            if cmde_line_opt.get('previous_run', None):
                if os.path.exists(cmde_line_opt['previous_run']):
                    options['previous_run'] = cmde_line_opt['previous_run']
                else:
                    raise ValueError( "previous run '%s' not found" % cmde_line_opt['previous_run'])
            try:
                options['sequence_db'] = self.parser.get( 'base', 'file', vars = cmde_line_opt )    
            except NoSectionError:
                sequence_db = cmde_line_opt.get( 'sequence_db' , None )
                if sequence_db is None:
                    raise ValueError( "No genome sequence file specified")
                else:
                    options['sequence_db'] = sequence_db
            if not os.path.exists(options['sequence_db']):
                raise ValueError( "%s: No such sequence data " % options['sequence_db'])
            
            val_4_db_type = ('unordered_replicon', 'ordered_replicon', 'gembase', 'unordered')
            if 'db_type' in cmde_line_opt:
                options['db_type'] = cmde_line_opt['db_type']
            else:
                try:
                    options['db_type'] = self.parser.get( 'base', 'type') 
                except (NoSectionError, NoOptionError):
                    raise ValueError( "you must specified the type of the genome base (%s)." %  ', '.join(val_4_db_type) )
            if options['db_type'] not in val_4_db_type:
                    raise ValueError( "allowed values for base type are : %s" % ', '.join(val_4_db_type))    
            val_4_replicon_topology = ('linear', 'circular')
            if 'replicon_topology' in cmde_line_opt:
                options['replicon_topology'] = cmde_line_opt['replicon_topology']
            else:
                try:
                    options['replicon_topology'] = self.parser.get( 'base', 'replicon_topology') 
                except (NoSectionError, NoOptionError):
                     options['replicon_topology'] = 'linear'
            if options['replicon_topology'] not in val_4_replicon_topology:
                    raise ValueError( "allowed values for base replicon_topology are : %s" % ', '.join(val_4_replicon_topology))         
            if options['replicon_topology'] == 'circular' and options['db_type'] in ( 'unordered_replicon', 'unordered' ):
                self._log.warning("db_type is set to %s, replicon_topology is ignored")
            try:
                options['hmmer_exe'] = self.parser.get('hmmer', 'hmmer_exe', vars = cmde_line_opt)
            except NoSectionError:
                if 'hmmer_exe' in cmde_line_opt:
                    options['hmmer_exe'] = cmde_line_opt['hmmer_exe']
                else:
                    options['hmmer_exe'] = self._defaults['hmmer_exe']
            try:
                e_value_res = self.parser.get('hmmer', 'e_value_res', vars = cmde_line_opt)
                options['e_value_res'] = float(e_value_res)
            except ValueError:
                msg = "Invalid value for hmmer e_value_res :{0}: (float expected)".format(e_value_res)
                raise ValueError( msg )
            except NoSectionError:
                if 'e_value_res' in cmde_line_opt:
                    options['e_value_res'] = float(cmde_line_opt['e_value_res'])
                else:
                    options['e_value_res'] = float(self._defaults['e_value_res'])
            try:
                i_evalue_sel = self.parser.get('hmmer', 'i_evalue_sel', vars = cmde_line_opt)
                options['i_evalue_sel'] = float(i_evalue_sel)
            except ValueError:
                msg = "Invalid value for hmmer i_evalue_sel :{0}: (float expected)".format(i_evalue_sel)
                raise ValueError( msg )
            except NoSectionError:
                if 'i_evalue_sel' in cmde_line_opt:
                    options['i_evalue_sel'] = float(cmde_line_opt['i_evalue_sel'])
                else:
                    options['i_evalue_sel'] = float(self._defaults['i_evalue_sel'])

            if options['i_evalue_sel'] > options['e_value_res']:
                raise ValueError( "i_evalue_sel (%f) must be lower or equal than e_value_res (%f)" %( options['i_evalue_sel'], options['e_value_res']) )

            try:
                coverage_profile = self.parser.get('hmmer', 'coverage_profile', vars = cmde_line_opt)
                options['coverage_profile'] = float(coverage_profile)
            except ValueError:
                msg = "Invalid value for hmmer coverage_profile :{0}: (float expected)".format(coverage_profile)
                raise ValueError( msg )
            except NoSectionError:
                if 'coverage_profile' in cmde_line_opt:
                    options['coverage_profile'] = float(cmde_line_opt['coverage_profile'])
                else:
                    options['coverage_profile'] = float(self._defaults['coverage_profile'])

            try:     
                options['def_dir'] = self.parser.get('directories', 'def_dir', vars = cmde_line_opt)
            except NoSectionError:
                if 'def_dir' in cmde_line_opt:
                    options['def_dir'] = cmde_line_opt['def_dir']
                else:
                    options['def_dir'] = self._defaults['def_dir']
            if not os.path.exists(options['def_dir']):
                raise ValueError( "%s: No such definition directory" % options['def_dir'])       

            

            try:
                options['profile_dir'] = self.parser.get('directories', 'profile_dir', vars = cmde_line_opt)
            except NoSectionError:
                if 'profile_dir' in cmde_line_opt:
                    options['profile_dir'] = cmde_line_opt['profile_dir']
                else:
                    options['profile_dir'] = self._defaults['profile_dir']
            if not os.path.exists( options['profile_dir'] ):
                raise ValueError( "%s: No such profile directory" % options['profile_dir'])

            try:
                options['res_search_suffix'] =  self.parser.get('directories', 'res_search_suffix', vars = cmde_line_opt)
            except NoSectionError:
                if 'res_search_suffix' in cmde_line_opt:
                    options['res_search_suffix'] = cmde_line_opt['res_search_suffix']
                else:
                    options['res_search_suffix'] = self._defaults['res_search_suffix']
            try:
                options['res_extract_suffix'] = self.parser.get('directories', 'res_extract_suffix', vars = cmde_line_opt)
            except NoSectionError:
                if 'res_extract_suffix' in cmde_line_opt:
                    options['res_extract_suffix'] = cmde_line_opt['res_extract_suffix']
                else:
                    options['res_extract_suffix'] = self._defaults['res_extract_suffix']
            try:
                options['profile_suffix'] = self.parser.get('directories', 'profile_suffix', vars = cmde_line_opt)
            except NoSectionError:
                if 'profile_suffix' in cmde_line_opt:
                    options['profile_suffix'] = cmde_line_opt['profile_suffix']
                else:
                    options['profile_suffix'] = self._defaults['profile_suffix']
            try:
                worker_nb = self.parser.get('general', 'worker_nb', vars = cmde_line_opt)
                
            except NoSectionError:
                if 'worker_nb' in cmde_line_opt:
                    worker_nb = cmde_line_opt['worker_nb']
                else:
                    worker_nb = self._defaults['worker_nb']
            try:
                worker_nb = int(worker_nb)
                if worker_nb >= 0:
                    options['worker_nb'] = worker_nb
            except ValueError:
                msg = "the number of worker must be an integer"
                raise ValueError( msg)

        except ValueError, err:
            self._log.error(str(err), exc_info= True)
            if working_dir:
                import shutil
                try:
                    shutil.rmtree(working_dir)
                except:
                    pass
            raise err
        return options

    def save(self, dir_path ):
        """
        save the configuration used for this run in ini format file
        """
        parser = SafeConfigParser()
        cfg_opts = [
                    ('hmmer', ('hmmer_exe', 'e_value_res', 'i_evalue_sel', 'coverage_profile' )),
                    ('directories', ('def_dir', 'res_search_dir', 'res_search_suffix', 'profile_dir', 'profile_suffix', 'res_extract_suffix')),
                    ('general', ('log_level', 'log_file', 'worker_nb'))
                    ]
        parser.add_section( 'base')
        parser.set( 'base', 'file', str(self.options['sequence_db']))
        parser.set( 'base', 'type', str(self.options['db_type']).lower())
                                                    
        for section , directives in cfg_opts:
            parser.add_section(section)
            for directive in directives:
                try:
                    if self.options[directive]:
                        if directive != 'log_file' or self.options[directive] != os.path.join( self.options['working_dir'], 'txsscan.log'):
                            parser.set( section, directive, str(self.options[directive]))
                except KeyError:
                    pass
        with open( os.path.join(dir_path, self._new_cfg_name), 'w') as new_cfg:
            parser.write(new_cfg)

    @property
    def sequence_db(self):
        """
        :return: the path to the sequence database
        :rtype: string 
        """
        return self.options['sequence_db']

    @property
    def db_type(self):
        """
        :return: the type of the sequences data base. the allowed values are :'unordered_replicon', 'ordered_replicon', 'gembase', 'unordered'
        :rtype: string
        """
        return self.options['db_type']

    @property
    def replicon_topology(self):
        """
        :return: the topology of the replicons. 2 values are supported 'linear' (default) and circular
        :rtype: string
        """
        return self.options['replicon_topology']
    
    @property
    def hmmer_exe(self):
        """
        :return: the name of the binary to excute to use profiles
        :rtype: string 
        """
        return self.options['hmmer_exe']

    @property
    def e_value_res(self):
        """
        :return: The e_value to apply for searching genes in sequences data base
        :rtype: float
        """
        return self.options['e_value_res']

    @property
    def i_evalue_sel(self):
        """
        :return: the i_evalue threshold to selct a hit in the hmm report
        :rtype: float
        """
        return self.options['i_evalue_sel']

    @property
    def coverage_profile(self):
        """
        :return: the coverage threshold to select a hit in the hmm report
        :rtype: float
        """
        return self.options['coverage_profile']

    @property
    def def_dir(self):
        """
        :return: the path to the directory where are the xml definitions of sectretion systems
        :rtype: string
        """
        return self.options['def_dir']

    @property
    def res_search_dir(self):
        """
        :return the path to the directory where are the results of txsscan runs
        :rtype: string
        """
        return self.options['res_search_dir']

    @property
    def working_dir(self):
        """
        :return: the path of the working directory of this run
        :rtpe: string
        """
        return self.options['working_dir']

    @property
    def res_search_suffix(self):
        """
        :return: the suffix for hmm output files
        :rtype: string
        """
        return self.options['res_search_suffix']

    @property
    def profile_dir(self):
        """
        :return: the path to the directory where are the gene profiles
        :rtype: string
        """
        return self.options['profile_dir']

    @property
    def profile_suffix(self):
        """
        :return: the suffix for profile files
        :rtype: string
        """
        return self.options['profile_suffix']

    @property
    def res_extract_suffix(self):
        """
        :return: the suffix of extract files (after HMM output parsing)
        :rtype: string
        """
        return self.options['res_extract_suffix']

    @property
    def worker_nb(self):
        """
        :return: the maximum number of parrallel jobs
        :rtype: int
        """
        return self.options.get('worker_nb', None)
    
    @property
    def previous_run(self):
        """
        :return: the path to previous run (directory) to use to recover hmm output
        :rtype: string
        """
        return self.options.get('previous_run', None)