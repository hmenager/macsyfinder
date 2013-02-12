# -*- coding: utf-8 -*-

#====================================
# Created on Nov 29, 2012
# 
# @author: bneron
# @contact: user_email
# @organization: organization_name
# @license: license
#====================================


import os
import logging
_log = logging.getLogger('txsscan.' + __name__)

from subprocess import Popen
from threading import Lock
from report import OrderedHMMReport, UnOrderedHMMReport


class GeneFactory(object):
    """
    build and cached all genes objects. Genes must not be instanciate directly.
    the gene_factory must be used. The gene factory ensure there is only one instance
    of gene for a given name.
    To get a gene use the method get_gene. if the gene is already cached this instance is returned
    otherwise a new gen is build, cached then returned.

    """
    _genes_bank = {}

    def get_gene(self, cfg, name, system, loner = False , exchangeable = False):
        """
        :return: return gene corresponding to the name.
                 If the gene already exists return it otherwise build it an d returni
        :rtype: :class:`txsscanlib.gene.Gene` object
        """
        if name in self._genes_bank:
            gene = self._genes_bank[name]
        else:
            gene = Gene(cfg, name, system, loner, exchangeable)
            self._genes_bank[name] = gene
        return gene

gene_factory = GeneFactory()

 
class Gene(object):
    """
    handle Gene of a secretion system

    """


    def __init__(self, cfg, name, system, loner = False, exchangeable = False ):
        """
        handle gene

        :param cfg: the configuration. 
        :type cfg: :class:`txsscanlib.config.Config` object
        :param name: the name of the gene.
        :type name: string.
        :param system: the system which belongs this gene/
        :type system: :class:`txsscanlib.system.System` object.
        :param loner: True if a gene can be isolated on the genome, False otherwise.
        :type loner: boolean.
        :param exchangeable: True if this gene can be replaced with one of its homologs whithout any effects on the system, False otherwise.
        :type exchangeable: boolean.
        """
        self.name = name 
        self.profile = profile_factory.get_profile(self, cfg)
        """:ivar profile: The profile HMM Profile corresponding to this gene :class:`txsscanlib.gene.Profile` object"""

        self.homologs = []
        self._system = system
        self._loner = loner
        self._exchangeable = exchangeable


    def __str__(self):
        s = "name : %s" % self.name
        if self.homologs:
            s += "\n    homologs: "
            for h in self.homologs:
                s += h.name + ", "
            s = s[:-2]
        return s

    @property
    def system(self):
        """
        :return: the secretion system to which this gene belongs
        :rtype: :class:`txsscanlib.system.System` object
        """
        return self._system

    @property
    def loner(self):
        """
        :return: True if the gene can be isolted on the genome false otherwise
        :rtype: boolean
        """
        return self._loner


    @property
    def exchangeable(self):
        """
        :return: True if this gene can be replaced with one of its homologs whithout any effects on the system, False otherwise.
        :rtype: boolean.
        """
        return self._exchangeable


    def add_homolog(self, homolog):
        """
        add a homolog gene

        :param homolog: homolog to add
        :type homolog:  :class:`txsscanlib.gene.Homolog` object 
        """
        self.homologs.append(homolog)


    def get_homologs(self):
        """
        :return: The homologs genes
        :type: list of :class:`txsscanlib.gene.Gene` object
        """
        return self.homologs
    
    def __eq__(self, gene):
        """
        :return: True if the profiles (genes) are the same, False otherwise.
        :type gene: :class:`txsscanlib.gene.Gene` object.
        :rtype: boolean.
        """
        return self.name == gene.name
        
        
    def is_homolog(self, gene):
        """
        :return: True if the genes are homologs, False otherwise.
        :type gene: :class:`txsscanlib.gene.Gene` object.
        :rtype: boolean.
        """
        if self == gene:
            return True
        else:
            for h in self.homologs:
                if self == h.gene:
                    return True
                
        return False       
        

class Homolog(object):
    """
    handle homologs
    """

    def __init__(self, gene, gene_ref, aligned = False ):
        """
        :param gene: the gene
        :type gene: :class:`txsscanlib.gene.Gene` object.
        :param gene_ref: the gene which this one is homolog.
        :type gene_ref: :class:`txsscanlib.gene.Gene` object.
        :param aligned: if True, this gene overlap totally the sequence of the gene reference. Otherwise it overlap partially. 
        :type aligned: boolean
        """
        self.gene = gene 
        """:ivar gene: gene """

        self.ref = gene_ref 
        self.aligned = aligned

    def __getattr__(self, name):
        return getattr(self.gene, name)

    def is_aligned(self):
        """
        :return: True if this homolog is aligned to its gene of reference, False otherwise.
        :rtype: boolean
        """
        return self.aligned

    @property
    def gene_ref(self):
        """
        :return: the gene of reference to this homolog
        :rtype: :class:`txsscanlib.gene.Gene` object
        """
        return self.ref


class ProfileFactory():
    """
    build and cached all Profile objects. Profiles must not be instanciate directly.
    the profile_factory must be used. The profile_factory ensure there is only one instance
    of profile for a given name.
    To get a profile use the method get_profile. If the profile is already cached this instance is returned
    otherwise a new profile is build, cached then returned.

    """
    _profiles = {}

    def get_profile(self, gene, cfg):
        """
        :return: return profile corresponding to the name.
                 If the profile already exists return it otherwise build it and return
        :rtype: :class:`txsscanlib.gene.Profile` object
        """
        if gene.name in self._profiles:
            profile = self._profiles[gene.name]
        else:
            profile = Profile(gene, cfg)
            self._profiles[gene.name] = profile
        return profile 

profile_factory = ProfileFactory()


class Profile(object):
    """
    handle profile
    """

    def __init__(self, gene , cfg):
        """

        :param gene: the gene corresponding to this profile
        :type gene_name: :class:`txsscanlib.secretion.Gene` object
        :param cfg: the configuration 
        :type cfg: :class:`txsscanlib.config.Config` object
        """
        self.gene = gene 
        path = os.path.join(cfg.profile_dir, self.gene.name + cfg.profile_suffix)
        if not os.path.exists(path):
            raise IOError( "%s: No such profile" % path)
        self.path = path
        self.len = self._len()
        self.cfg = cfg 
        self.hmm_raw_output = None
        self._report = None
        self._lock = Lock()


    def __len__(self):
        """
        :return: the length of the HMM profile
        :rtype: int
        """
        return self.len

    def _len(self):
        """
        Parse the HMM profile to get the length and cache it
        this private method is called at the Profile init
        """
        with open(self.path) as f:
            for l in f:
                if l.startswith("LENG"):
                    length = int(l.split()[1])
                    break
        return length

    def __str__(self):
        return "%s : %s" % (self.gene.name, self.path)


    def execute(self):
        """
        execute the hmmsearch with this profile

        :return: an HMM report
        :rtype:  :class:`txsscanlib.report.HMMReport` object
        """
        with self._lock:
            # the results of HMM is cached 
            # so HMMsearch is executed only once per run
            # if this method is called several times the first call induce the execution of HMMsearch and generate a report
            # the other calls return directly this report
            if self._report is not None:
                return self._report
            output_path = os.path.join( self.cfg.working_dir, self.gene.name + self.cfg.res_search_suffix )
            err_path = os.path.join( self.cfg.working_dir, self.gene.name + os.path.splitext(self.cfg.res_search_suffix)[0]+".err" )

            with  open(err_path, 'w') as err_file:
                options = { "hmmer_exe" : self.cfg.hmmer_exe,
                            "output_file" : output_path ,
                            "e_value_res" : self.cfg.e_value_res,
                            "profile" : self.path,
                            "sequence_db" : self.cfg.sequence_db,
                           }
                command = "%(hmmer_exe)s -o %(output_file)s -E %(e_value_res)d %(profile)s %(sequence_db)s" % options
                _log.info( "%s hmmer command line : %s" % (self.gene.name, command) )
                try:
                    hmmer = Popen( command ,
                                   shell = True ,
                                   stdout = None ,
                                   stdin  = None ,
                                   stderr = err_file ,
                                   close_fds = False ,
                                   )
                except Exception, err:
                    msg = "hmmer execution failed: command = %s : %s" % ( command , err)
                    _log.critical( msg, exc_info = True )
                    raise err

                hmmer.wait()
            if hmmer.returncode != 0:
                msg = "an error occurred during hmmer execution: command = %s : return code = %d check %s" % (command, hmmer.returncode, err_path)
                _log.critical( msg, exc_info = True )
                raise RuntimeError(msg)
            self.hmm_raw_output = output_path
            if self.cfg.db_type == 'gembase':
                report = OrderedHMMReport(self.gene, output_path, self.cfg )
            else:
                report = UnOrderedHMMReport(self.gene, output_path, self.cfg )
            self._report = report
            return report
            