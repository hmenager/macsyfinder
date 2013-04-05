# -*- coding: utf-8 -*-

###############################
# Created on Feb 14, 2013
#
# @author: sabby
# @contact: sabby@pasteur.fr
# @organization: Institut Pasteur
# @license: GPLv3
################################

import threading
import logging
from report import Hit # required? 
#from operator import attrgetter # To be used by the groupby()
#from itertools import groupby
import itertools, operator
_log = logging.getLogger('txsscan.' + __name__)


class ClustersHandler(object):
    """
    Deals with sets of clusters found in a dataset. Conceived to store only clusters for a same replicon.
    """
    
    def __init__(self, cfg):
        """
        :param cfg: The configuration object built from default and user parameters.
        :type cfg: :class:`txsscanlib.config.Config` 
        """
        self.clusters = []
        self.replicon_name = ""
    
    def add(self, cluster):
        if not self.replicon_name:
            self.replicon_name = cluster.replicon_name            
            cluster.save()
            self.clusters.append(cluster)
        elif self.replicon_name == cluster.replicon_name:            
            cluster.save()
            self.clusters.append(cluster)
        else:
            msg = "Attempting to add a cluster in a ClustersHandler dedicated to another replicon !"
            _log.critical(msg)
            raise Exception(msg)
        
    def __str__(self):
        to_print=""
        for cluster in self.clusters:
            to_print+=str(cluster)
            
        return to_print

                        
class Cluster(object):
    """
    Stores a set of contiguous hits. 
    """
    
    def __init__(self, cfg):
        self.hits = []
        self.systems = []
        self.replicon_name = ""
        self.begin = 0
        self.end = 0
        self.state = ""
        self.putative_system = ""
        #self.add(hit)
    
    def __len__(self):
        return len(self.hits)
    
    def __str__(self):
        
        pos = []
        seq_ids = []
        gene_names = [] 
        for h in self.hits:
            pos.append(h.position)
            seq_ids.append(h.id)
            gene_names.append(h.gene.name)
            
        #return "--- Cluster ---\n%s\n%s\n%s"%(str(seq_ids), str(gene_names), str(pos))
        if self.state == "clear":
            return "--- Cluster %s ---\n%s\n%s\n%s"%(self.putative_system, str(seq_ids), str(gene_names), str(pos))
        else:
            return "--- Cluster %s ? ---\n%s\n%s\n%s"%(self.putative_system, str(seq_ids), str(gene_names), str(pos))
        
    def add(self, hit):
        # need to update cluster bounds
        if len(self.hits) == 0:
            self.begin = hit.get_position()
            self.end = self.begin
            self.replicon_name = hit.replicon_name
            self.hits.append(hit)
        else:
            if(self.replicon_name == hit.replicon_name):
                if hit.get_position() < self.begin:
                    self.begin = hit.get_position()
                elif hit.get_position() > self.end:
                    self.end = hit.get_position()
                else:
                    if hit.get_position() > self.begin and hit.get_position() < self.end:
                        _log.debug("Weird cluster inclusion hit : %s"%hit)
                            
                self.hits.append(hit)
                
            else:
                msg = "Attempting to gather in a cluster hits from different replicons ! "
                _log.critical(msg)
                raise Exception(msg)
                    
    def save(self):
        
        if not self.putative_system:
            systems={}
            genes=[]
            for h in self.hits:
                syst=h.system.name
                if not systems.has_key(syst):
                    systems[syst]=1
                else:
                    systems[syst]+=1
                if genes.count(h.gene.name) == 0:
                    genes.append(h.gene.name)

            max_syst=0
            tmp_syst_name=""
            for x,y in systems.iteritems():
                if y>=max_syst:
                    tmp_syst_name=x
                    max_syst=y
            
            self.putative_system = tmp_syst_name
            self.systems=systems

            if len(genes) == 1 and self.hits[0].gene.loner == False:
                self.state = "ineligible"
            else:
                if len(systems.keys()) == 1:
                    self.state = "clear"
                else:
                    self.state = "ambiguous"

    #def is_eligible(self):
    #    for h in hits:
            

def build_clusters(hits, cfg):
    """
    Gets sets of contiguous hits according to the minimal inter_gene_max_space between two genes. Only for \"ordered\" datasets. 
    Remains to do : 
    
    - Implement case of circular replicons => need to store max position for each replicon ! and update... 
    - Runs on data grouped by replicon : does not check that genes from different replicons are not aggregated in a cluster (but functions Cluster and ClustersHandler do) 
    
    :param hits: a list of Hmmer hits to analyze 
    :type hits: a list of :class:`txsscanlib.report.Hit`
    :param cfg: the configuration object built from default and user parameters.
    :type cfg: :class:`txsscanlib.config.Config`
    :return: a set of clusters
    :rtype: :class:`txsscanlib.search_systems.ClustersHandler`
    """    
    
    _log.debug("Starting cluster detection with build_clusters... ")
    
    # Deals with different dataset types using Pipeline ?? 
    clusters = ClustersHandler(cfg)
    prev = hits[0]
    cur_cluster = Cluster(cfg)
    positions = []
    loner_state=False
    
    tmp=""
    for cur in hits[1:]:
        
        prev_max_dist = prev.get_syst_inter_gene_max_space()
        cur_max_dist = cur.get_syst_inter_gene_max_space()
        inter_gene = cur.get_position() - prev.get_position() - 1
        
        tmp="\n****\n"
        tmp+="prev_max_dist : %d\n"%(prev_max_dist)
        tmp+="cur_max_dist : %d\n"%(cur_max_dist)
        tmp+="Intergene space : %d\n"%(inter_gene)
        tmp+="Cur : %s"%cur
        tmp+="Prev : %s"%prev
        tmp+="Len cluster: %d\n"%len(cur_cluster)
        
        #print tmp
        
        # First condition removes duplicates (hits for the same sequence)
        # the two others takes into account either system1 parameter or system2 parameter    
        if(inter_gene <= prev_max_dist or inter_gene <= cur_max_dist ):
        # First check the cur.id is different from  the prev.id !!!
        #if(inter_gene!=-1 and (inter_gene <= prev_max_dist or inter_gene <= cur_max_dist )):
            #print "zero"
            if positions.count(prev.position) == 0:
                #print "un - ADD prev in cur_cluster"
                cur_cluster.add(prev)
                positions.append(prev.position)
                
            if positions.count(cur.position) == 0:
                #print "deux - ADD cur in cur_cluster"
                cur_cluster.add(cur)
                positions.append(cur.position)
                
            if prev.gene.loner:
                # PB !!!! Do not enter here when T3SS sctC loner and T2SS searched too... CHECK !!
                #print "trois - loner_state"
                #print "--- PREVLONER %s %s"%(prev.id, prev.gene.name)
                loner_state = True
        else:
            # Storage of the previous cluster
            if len(cur_cluster)>1:
                #print cur_cluster
                #print "quatre - ADD cur_cluster"
                clusters.add(cur_cluster) # Add an in-depth copy of the object? 
                #print(cur_cluster)
                
                cur_cluster = Cluster(cfg) 
                loner_state = False
                
            elif len(cur_cluster) == 1 and loner_state == True: # WTF?
                #print cur_cluster
                #print "cinq - ADD cur_cluster"
                #print "LNOER??"
                #print "PREVLONER %s %s"%(prev.id, prev.gene.name)
                clusters.add(cur_cluster) # Add an in-depth copy of the object? 
                #print(cur_cluster)
                    
                cur_cluster = Cluster(cfg) 
                loner_state = False
            
            if prev.gene.loner:
                #print "six - check"
                #print "PREVLONER ?? %s %s"%(prev.id, prev.gene.name)
                
                if positions.count(prev.position) == 0:
                    #print "six - ADD prev in cur_cluster, ADD cur_cluster"
                    cur_cluster.add(prev) 
                    clusters.add(cur_cluster) 
                    #print(cur_cluster)
                    
                    positions.append(prev.position)
                    loner_state = False  
                    cur_cluster = Cluster(cfg)  
                
            cur_cluster = Cluster(cfg)     
            
        prev=cur
    
    # !!! Treat the last cluster?     
    return clusters


class SystemOccurence(object):
    """
    This class is instantiated for a system that has been asked for detection. It can be filled step by step with hits. 
    A decision can then be made according to parameters defined *e.g.* quorum of genes.     
    """
    def __init__(self, system):
        """
        :param system: the system to \"fill\" with hits.
        :type system: :class:`txsscanlib.system.System` 
        """
        self.system = system
        self.system_name = system.name
        # Make those attributes non modifiable?
        self.mandatory_genes = {}
        self.exmandatory_genes = {} # List of 'exchanged' mandatory genes
        for g in system.mandatory_genes:
            self.mandatory_genes[g.name]=0
            if g.exchangeable:
                homologs=g.get_homologs()
                for h in homologs:
                    self.exmandatory_genes[h.name] = g.name
        
        self.allowed_genes = {}
        self.exallowed_genes = {} # List of 'exchanged' allowed genes
        for g in system.allowed_genes:
            self.allowed_genes[g.name]=0
            if g.exchangeable:
                homologs=g.get_homologs()
                for h in homologs:
                    self.exallowed_genes[h.name] = g.name
        
        self.forbidden_genes = {}
        for g in system.forbidden_genes:
            self.forbidden_genes[g.name]=0
        
        #self.mandatory_genes = system.mandatory_genes
        #self.allowed_genes = system.allowed_genes
        #self.forbidden_genes = system.forbidden_genes
        
        self.state = "empty"
        self.nb_cluster = 0
                 
    def __str__(self):
        out=""
        if self.mandatory_genes: 
            out+="Mandatory genes: \n"
            for k, g in self.mandatory_genes.iteritems():
                out+="%s\t%d\n"%(k, g) 
        if self.allowed_genes:
            out+="Allowed genes: \n"  
            for k, g in self.allowed_genes.iteritems():
                out+="%s\t%d\n"%(k, g)  
        if self.forbidden_genes:
            out+="Forbidden genes: \n"  
            for k, g in self.forbidden_genes.iteritems():
                out+="%s\t%d\n"%(k, g)   
        return out
        
    def fill_with(self, cluster):
        """
        Adds hits from a cluster to a system occurence, and check which are their status according to the system definition.
        
        :param cluster: the set of contiguous genes to treat for :class:`txsscanlib.search_systems.SystemOccurence` inclusion. 
        :type cluster: :class:`txsscanlib.search_systems.Cluster`
        :return: True if the system occurence is completed with this cluster given input parameters of quorum, and False otherwise (cf. :func:`txsscanlib.search_systems.SystemOccurence.decide`) 
        :rtype: boolean
        
        """
        #so_cl=SystemOccurence(self.system)
        self.nb_cluster += 1
        for hit in cluster.hits:
            # Need to check first that this cluster is eligible for system inclusion
            #
            
            if hit.gene.is_mandatory(self.system):
                self.mandatory_genes[hit.gene.name]+=1
            elif hit.gene.is_allowed(self.system):
                self.allowed_genes[hit.gene.name]+=1
            elif hit.gene.is_forbidden(self.system):
                self.forbidden_genes[hit.gene.name]+=1
            else:
                if hit.gene.name in self.exmandatory_genes.keys():
                    self.mandatory_genes[self.exmandatory_genes[hit.gene.name]]+=1
                elif hit.gene.name in self.exallowed_genes.keys():
                    self.allowed_genes[self.exallowed_genes[hit.gene.name]]+=1
                else:
                    #print "Foreign gene %s in cluster %s"%(hit.gene.name, self.system_name)
                    msg="Foreign gene %s in cluster %s"%(hit.gene.name, self.system_name)
                    print msg
                    #_log.info(msg)
        
        #return self.decide()

    def count_genes(self, gene_dict):
        total = 0
        for v in gene_dict.values():
            if v>0:
                total+=1
        return total
                
    def decide(self):
        #if (self.count_genes(self.forbidden_genes) == 0 and self.count_genes(self.mandatory_genes) >= self.system.min_mandatory_genes_required and (self.count_genes(self.mandatory_genes) + self.count_genes(self.allowed_genes)) >= self.system.min_system_genes_required):
        nb_forbid = self.count_genes(self.forbidden_genes)
        nb_mandat = self.count_genes(self.mandatory_genes)
        nb_allowed = self.count_genes(self.allowed_genes)
        nb_genes = nb_mandat + nb_allowed

        msg = "====> Decision rule for putative system %s\n"%self.system_name
        msg += str(self)
        msg += "\nnb_forbid : %d\nnb_mandat : %d\nnb_allowed : %d"%(nb_forbid, nb_mandat, nb_allowed)
               
        if ( nb_forbid == 0 and nb_mandat >= (len(self.mandatory_genes)-3) and nb_genes >= (len(self.mandatory_genes) + len(self.allowed_genes) - 4) and nb_genes >= 2):
           
            if self.nb_cluster == 1: 
                self.state = "single_locus"
            else:
                self.state = "multi_loci"
                
            msg += "\nYeah complete system \"%s\"."%self.state
            print msg
            #_log.info(msg)
            return True
        else:
            msg += "\nuncomplete system."
            print msg
            #_log.info(msg)
            self.state = "uncomplete"
            return False
        

def analyze_clusters_replicon(clusters, systems, cfg):
    """
    Analyzes sets of contiguous hits (clusters) stored in a ClustersHandler for system detection:
        
    - split clusters if needed
    - delete them if they are not relevant
    - check the QUORUM for each system to detect, *i.e.* mandatory + allowed - forbidden
          
    Only for \"ordered\" datasets representing a whole replicon. 
    Reports systems occurence. 
    
    :param clusters: the set of clusters to analyze
    :type clusters: :class:`txsscanlib.search_systems.ClustersHandler` 
    :param systems: the set of systems to detect
    :type systems: a list of :class:`txsscanlib.system.System`
    :return: a set of systems occurence filled with hits found in clusters
    :rtype: a list of :class:`txsscanlib.search_systems.SystemOccurence` 
    
    """
    
    # Global Hits collectors, for uncomplete cluster Hits
    systems_occurences={}
    #for system in systems:
    #    systems_occurences[system.name]=SystemOccurence(system)    
    syst_dict={}
    for system in systems:
        syst_dict[system.name]=system
        systems_occurences[system.name]=SystemOccurence(system)
    
    for clust in clusters.clusters:
        if clust.state == "clear":
            #so=systems_occurences[clust.putative_system]
            
            #print "\n@@@@@@@--- CHECK current cluster ---@@@@@@@" 
            print "\n%s"%str(clust)
            # Local Hits collector
            so=SystemOccurence(syst_dict[clust.putative_system])
            #decision = so.fill_with(clust)
            so.fill_with(clust)
            decision = so.decide()
            if decision:
                print "...\nComplete system stored.\n"
                #pass
            else:
                # Store it to pool genes found with genes from other clusters.
                #if not systems_occurences.has_key(clust.putative_system):
                #    systems_occurences[clust.putative_system]=[]
                #    systems_occurences[clust.putative_system].append(so)
                #else:
                #    systems_occurences[clust.putative_system].append(so)
                print "...\nStored for later treatment of scattered systems.\n"
                systems_occurences[clust.putative_system].fill_with(clust)
                
            #print so
            
        #break
    print "\n\n*****************************************\n******* Report scattered systems *******\n*****************************************\n"
    for system in systems:
        #print systems_occurences[system]
        if systems_occurences[system.name].decide():
            print "\n******************************************\n"




def search_systems(hits, systems, cfg):
    """
    Runs systems search from hits according to the kind of database provided. 
    Analyze quorum and colocalization if required for system detection. 
    """

    if cfg.db_type == 'gembase':
        #build_clusters(hits, cfg)
        
        # Use of the groupby() function from itertools : allows to group Hits by replicon_name, 
        # and then apply the same build_clusters functions to replicons from "gembase" and "ordered_replicon" types of databases.
                
        #build_clusters(sub_hits, cfg) for sub_hits in [list(g) for k, g in itertools.groupby(hits, operator.attrgetter('replicon_name'))]
        for k, g in itertools.groupby(hits, operator.attrgetter('replicon_name')):
            sub_hits=list(g)
            #print "\n************\nBuilding clusters for %s \n************\n"%k
            clusters=build_clusters(sub_hits, cfg)
            #print "\n************\nAnalyzing clusters for %s \n************\n"%k
            analyze_clusters_replicon(clusters, systems, cfg)
            #break
            
    elif cfg.db_type == 'ordered_replicon':
        clusters=build_clusters(hits, cfg)
    elif cfg.db_type == 'unordered_replicon':
        pass
    elif cfg.db_type == 'unordered':
        pass
    else:
        raise ValueError("Invalid database type. ")




